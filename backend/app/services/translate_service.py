import asyncio
import json
import logging
from typing import Optional, List

from app.config import settings
from app.models.schemas import TranslateStyle
from app.services.llm_provider import (
    MODEL_TRANSLATE,
    MODEL_VISION,
    build_provider,
)

logger = logging.getLogger(__name__)

# 형식 강제용 도구. 실행할 함수는 존재하지 않는다 —
# LLM 이 채워 보낸 인자 자체가 결과다(ADR-002).
BATCH_TRANSLATION_TOOL = {
    "name": "submit_translations",
    "description": (
        "번역 결과를 제출한다. 입력으로 받은 각 항목의 번호를 index 로 그대로 사용하고, "
        "빠뜨리거나 합치지 말고 입력 개수와 정확히 같은 수의 항목을 제출한다."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer", "description": "입력 번호(1부터)"},
                        "text": {"type": "string", "description": "번역된 텍스트"},
                    },
                    "required": ["index", "text"],
                },
            }
        },
        "required": ["items"],
    },
}

IMAGE_ANALYSIS_TOOL = {
    "name": "report_bubbles",
    "description": "이미지에서 찾은 말풍선의 원문·번역·위치를 제출한다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "texts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "original": {"type": "string"},
                        "translated": {"type": "string"},
                        "type": {"type": "string"},
                        "bbox": {
                            "type": "array",
                            "items": {"type": "number"},
                            "minItems": 4,
                            "maxItems": 4,
                            "description": "[x%, y%, w%, h%] 말풍선 테두리 안쪽",
                        },
                    },
                    "required": ["original", "translated", "bbox"],
                },
            }
        },
        "required": ["texts"],
    },
}


class TranslateService:
    """번역 서비스. LLM 호출 경로는 llm_provider 가 정한다(SDK 우선, CLI 폴백)."""

    def __init__(self, timeout: int = None):
        self.timeout = timeout or settings.CLAUDE_TIMEOUT
        self.provider = build_provider(self.timeout)

    async def translate(
        self,
        text: str,
        source_language: str = "일본어",
        target_language: str = "한국어",
        style: TranslateStyle = TranslateStyle.MANGA,
        context: Optional[str] = None
    ) -> str:
        """
        텍스트 번역

        Args:
            text: 번역할 텍스트
            source_language: 원본 언어
            target_language: 목표 언어
            style: 번역 스타일
            context: 추가 컨텍스트

        Returns:
            번역된 텍스트
        """
        style_guide = {
            TranslateStyle.FORMAL: "존댓말로 격식있게",
            TranslateStyle.CASUAL: "반말로 자연스럽게",
            TranslateStyle.MANGA: "만화 대사답게 자연스럽고 생동감있게"
        }

        prompt = f"""다음 {source_language} 텍스트를 {target_language}로 번역해줘.
{f'컨텍스트: {context}' if context else ''}
스타일: {style_guide[style]}

번역할 텍스트:
{text}

번역 결과만 출력해줘. 설명이나 부연 없이 번역된 텍스트만."""

        return await self._call_claude(prompt)

    async def translate_batch(
        self,
        texts: List[str],
        target_language: str = "한국어",
        style: TranslateStyle = TranslateStyle.MANGA
    ) -> List[str]:
        """여러 텍스트 일괄 번역.

        SDK 경로에서는 스키마를 강제해 index 를 명시적으로 받고, 개수·인덱스 집합을
        검증한다. 어긋나면 원문으로 폴백한다 — 대사 밀림은 에러가 아니라 «잘못된 화면»
        으로 나타나므로, 조용히 통과시키지 않는 쪽을 택했다(ADR-002).

        CLI 경로에서는 스키마를 쓸 수 없어 기존 문자열 파싱으로 폴백한다.
        """
        if not texts:
            return []

        numbered_texts = "\n".join(
            f"{i+1}. {text}" for i, text in enumerate(texts)
        )
        prompt = f"""다음 일본어 텍스트들을 {target_language}로 번역해줘.
만화 대사답게 자연스럽게 번역해줘.

{numbered_texts}

각 항목의 번호(index)를 그대로 유지하고, 총 {len(texts)}개를 빠짐없이 제출해줘."""

        # ── SDK 경로: 스키마 강제 ──────────────────────────────
        data = await self.provider.complete_tool(
            prompt, tool=BATCH_TRANSLATION_TOOL, model=MODEL_TRANSLATE, max_tokens=4096
        )
        if data is not None:
            ok, translations = self._validate_batch(data, texts)
            if ok:
                return translations
            return list(texts)  # 검증 실패 → 청크 전체 원문 폴백

        # ── CLI 경로: 문자열 파싱 폴백 ─────────────────────────
        return await self._translate_batch_by_text(prompt, texts)

    @staticmethod
    def _validate_batch(data: dict, texts: List[str]) -> tuple[bool, List[str]]:
        """개수와 인덱스 집합을 검증한다.

        개수만 맞고 순서가 밀린 경우를 잡기 위해 인덱스 집합까지 본다 —
        기존 폴백(부족한 만큼만 원문으로 채우기)이 놓치던 지점이 정확히 여기다.
        """
        items = data.get("items") or []
        n = len(texts)

        if len(items) != n:
            logger.warning("배치 번역 개수 불일치: 입력 %d → 응답 %d", n, len(items))
            return False, []

        try:
            indexed = {int(it["index"]): str(it["text"]) for it in items}
        except (KeyError, TypeError, ValueError) as e:
            logger.warning("배치 번역 항목 형식 오류: %s", e)
            return False, []

        if set(indexed) != set(range(1, n + 1)):
            missing = set(range(1, n + 1)) - set(indexed)
            extra = set(indexed) - set(range(1, n + 1))
            logger.warning("배치 번역 인덱스 불일치: 누락=%s 초과=%s", missing, extra)
            return False, []

        return True, [indexed[i] for i in range(1, n + 1)]

    async def _translate_batch_by_text(self, prompt: str, texts: List[str]) -> List[str]:
        """CLI 경로 폴백. 형식을 지킨다는 보장이 없으므로 개수 검증을 함께 한다."""
        result = await self._call_claude(
            prompt + "\n\n형식:\n1. [번역결과]\n2. [번역결과]"
        )

        translations = []
        for line in result.strip().split("\n"):
            if ". " in line:
                _, translation = line.split(". ", 1)
                translations.append(translation.strip())

        if len(translations) != len(texts):
            logger.warning(
                "CLI 파싱 개수 불일치: 입력 %d → 파싱 %d, 원문으로 폴백",
                len(texts), len(translations),
            )
            return list(texts)
        return translations

    async def translate_batch_parallel(
        self,
        texts: List[str],
        target_language: str = "한국어",
        style: TranslateStyle = TranslateStyle.MANGA,
        chunk_size: int = 15,
        concurrency: int = 4,
    ) -> List[str]:
        """텍스트를 청크로 나눠 claude CLI를 병렬 호출 (독립 프로세스, 동시성 제한).

        단일 호출(텍스트 수에 비례해 느림) 대비, 청크를 동시에 번역해 벽시계 시간 단축.
        청크별로 길이에 맞춰 정렬해 전역 인덱스 어긋남을 방지한다.
        """
        if not texts:
            return []
        if len(texts) <= chunk_size:
            return await self.translate_batch(texts, target_language, style)

        chunks = [texts[i:i + chunk_size] for i in range(0, len(texts), chunk_size)]
        sem = asyncio.Semaphore(concurrency)

        async def run(chunk):
            async with sem:
                return await self.translate_batch(chunk, target_language, style)

        results = await asyncio.gather(*[run(c) for c in chunks], return_exceptions=True)

        out = []
        for chunk, res in zip(chunks, results):
            if isinstance(res, Exception) or not isinstance(res, list):
                out.extend(chunk)  # 실패 시 원문 폴백
            else:
                for i, original in enumerate(chunk):
                    out.append(res[i] if i < len(res) else original)
        return out

    async def analyze_and_translate_image(
        self,
        image_path: str,
        target_language: str = "한국어"
    ) -> dict:
        """Claude Vision 으로 이미지 분석 및 번역.

        주 파이프라인은 로컬 모델(YOLOv8 → MobileSAM → manga-ocr)이 담당하고,
        이 경로는 보조/비교용이다. 좌표 정확도와 비용 모두 로컬 쪽이 낫다.
        """
        prompt = f"""{image_path} 파일을 분석해줘.

이 만화 이미지의 모든 말풍선/텍스트를 찾아 {target_language}로 번역해줘.

bbox 좌표 규칙:
- bbox = [x%, y%, width%, height%] (백분율, 소수점 사용 가능)
- 말풍선 테두리 **안쪽** 영역만 포함
- 텍스트가 실제로 있는 영역보다 **약간 작게**
- 좌표계: 왼쪽=0%, 오른쪽=100%, 위=0%, 아래=100%"""

        # SDK 경로: 스키마 강제 — JSON 을 문자열에서 긁어내지 않는다
        data = await self.provider.complete_tool(
            prompt, tool=IMAGE_ANALYSIS_TOOL, model=MODEL_VISION, max_tokens=4096
        )
        if data is not None:
            return {"texts": data.get("texts", [])}

        # CLI 경로 폴백: 텍스트에서 JSON 추출
        result = await self._call_claude(
            prompt + '\n\nJSON만 출력:\n{"texts": [{"original": "", "translated": "", "type": "dialogue", "bbox": [0,0,0,0]}]}'
        )
        try:
            start_i, end_i = result.find("{"), result.rfind("}") + 1
            if start_i != -1 and end_i > start_i:
                return json.loads(result[start_i:end_i])
        except json.JSONDecodeError:
            logger.warning("이미지 분석 JSON 파싱 실패")
        return {"texts": [], "raw_response": result}

    async def _call_claude(self, prompt: str, *, model: str = None) -> str:
        """자유 텍스트 호출. 실제 경로(SDK/CLI)는 provider 가 정한다."""
        return await self.provider.complete(
            prompt, model=model or MODEL_TRANSLATE, max_tokens=2048
        )


# 싱글톤 인스턴스
translate_service = TranslateService()
