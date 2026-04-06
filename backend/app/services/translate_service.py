import subprocess
import asyncio
import json
from typing import Optional, List

from app.config import settings
from app.models.schemas import TranslateStyle


class TranslateService:
    """Claude Code CLI를 사용한 번역 서비스"""

    def __init__(self, timeout: int = None):
        self.timeout = timeout or settings.CLAUDE_TIMEOUT

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
        """
        여러 텍스트 일괄 번역

        Args:
            texts: 번역할 텍스트 리스트
            target_language: 목표 언어
            style: 번역 스타일

        Returns:
            번역된 텍스트 리스트
        """
        numbered_texts = "\n".join(
            f"{i+1}. {text}" for i, text in enumerate(texts)
        )

        prompt = f"""다음 일본어 텍스트들을 {target_language}로 번역해줘.
만화 대사답게 자연스럽게 번역하고, 번호를 유지해서 출력해줘.

{numbered_texts}

형식:
1. [번역결과]
2. [번역결과]
..."""

        result = await self._call_claude(prompt)

        # 결과 파싱
        translations = []
        for line in result.strip().split("\n"):
            # "1. 번역결과" 형식에서 번역결과만 추출
            if ". " in line:
                _, translation = line.split(". ", 1)
                translations.append(translation.strip())

        return translations

    async def analyze_and_translate_image(
        self,
        image_path: str,
        target_language: str = "한국어"
    ) -> dict:
        """
        Claude Vision으로 이미지 분석 및 번역

        Args:
            image_path: 이미지 파일 경로
            target_language: 목표 언어

        Returns:
            {"texts": [{"original": ..., "translated": ..., "location": ..., "type": ..., "bbox": ...}]}
        """
        prompt = f"""{image_path} 파일을 분석해줘.

이 만화 이미지의 모든 말풍선/텍스트를 찾아 {target_language}로 번역해줘.

bbox 좌표 규칙 (매우 중요 - 정확히 따라줘):
- bbox = [x%, y%, width%, height%] (백분율, 소수점 사용 가능)
- 말풍선 테두리 **안쪽** 영역만 포함 (테두리 밖으로 나가면 안됨)
- 텍스트가 실제로 있는 영역보다 **약간 작게** 잡아줘
- 좌표계: 왼쪽=0%, 오른쪽=100%, 위=0%, 아래=100%

예시: 작은 말풍선이면 width, height도 작게 (예: 15%, 10%)

JSON만 출력:
{{"texts": [{{"original": "원문", "translated": "번역", "type": "dialogue", "bbox": [x, y, w, h]}}]}}"""

        result = await self._call_claude(prompt)

        # JSON 추출
        try:
            # JSON 부분만 추출
            start = result.find("{")
            end = result.rfind("}") + 1
            if start != -1 and end > start:
                json_str = result[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        return {"texts": [], "raw_response": result}

    async def _call_claude(self, prompt: str) -> str:
        """
        Claude Code CLI 호출

        Args:
            prompt: 프롬프트

        Returns:
            Claude 응답
        """
        # 특수문자 이스케이프
        escaped_prompt = prompt.replace('"', '\\"').replace('`', '\\`').replace('$', '\\$')

        cmd = f'claude -p "{escaped_prompt}" --output-format text'

        try:
            # 비동기로 subprocess 실행
            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout
            )

            if process.returncode != 0:
                raise Exception(f"Claude CLI error: {stderr.decode()}")

            return stdout.decode().strip()

        except asyncio.TimeoutError:
            raise Exception(f"Claude CLI timeout after {self.timeout}s")


# 싱글톤 인스턴스
translate_service = TranslateService()
