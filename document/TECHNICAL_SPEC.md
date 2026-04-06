# Technical Specification

## 1. 시스템 요구사항

### 하드웨어 최소 요구사항
| 항목 | 최소 | 권장 |
|------|------|------|
| CPU | 4코어 | 8코어 이상 |
| RAM | 8GB | 16GB 이상 |
| 저장공간 | 10GB | 20GB 이상 |
| GPU | 없어도 됨 | NVIDIA GPU (lama-cleaner 가속) |

### 소프트웨어 요구사항
| 소프트웨어 | 버전 | 용도 |
|------------|------|------|
| Python | 3.9 - 3.11 | Backend |
| Node.js | 18.x 이상 | Frontend |
| Claude Code CLI | 최신 | 번역 |
| cloudflared | 최신 | 외부 접속 (선택) |

---

## 2. Backend 상세 (Python FastAPI)

### 2.1 프로젝트 구조

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 앱 진입점
│   ├── config.py               # 환경 설정
│   ├── dependencies.py         # 의존성 주입
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── process.py          # /api/process - 전체 파이프라인
│   │   ├── translate.py        # /api/translate - 번역만
│   │   └── ocr.py              # /api/ocr - OCR만
│   ├── services/
│   │   ├── __init__.py
│   │   ├── ocr_service.py      # manga-ocr 래퍼
│   │   ├── translate_service.py # Claude CLI 래퍼
│   │   ├── inpaint_service.py  # 텍스트 제거
│   │   └── render_service.py   # 텍스트 렌더링
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic 모델
│   └── utils/
│       ├── __init__.py
│       └── image_utils.py      # 이미지 유틸리티
├── uploads/                    # 업로드 파일 저장
├── outputs/                    # 결과 파일 저장
├── fonts/                      # 한글 폰트
├── requirements.txt
├── .env                        # 환경 변수
└── run.py                      # 실행 스크립트
```

### 2.2 requirements.txt

```text
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# OCR
manga-ocr==0.1.8
torch>=2.0.0
torchvision>=0.15.0

# Image Processing
Pillow>=10.0.0
opencv-python>=4.8.0
numpy>=1.24.0

# Inpainting (선택)
# lama-cleaner==1.2.4

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
pydantic-settings==2.1.0
aiofiles==23.2.1
```

### 2.3 main.py - FastAPI 앱

```python
# app/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os

from app.config import settings
from app.routers import process, translate, ocr
from app.services.ocr_service import OCRService

# 전역 OCR 서비스 (모델 로딩 시간 절약)
ocr_service: OCRService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 로직"""
    global ocr_service

    # 시작 시: OCR 모델 미리 로드
    print("Loading OCR model...")
    ocr_service = OCRService()
    print("OCR model loaded!")

    # 디렉토리 생성
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    yield

    # 종료 시: 정리 작업
    print("Shutting down...")


app = FastAPI(
    title="Anime Transformer API",
    description="만화 이미지 번역 API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS 설정 (Frontend에서 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Next.js 개발 서버
        "http://127.0.0.1:3000",
        settings.FRONTEND_URL,         # 프로덕션 URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (결과 이미지)
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")

# 라우터 등록
app.include_router(process.router, prefix="/api", tags=["Process"])
app.include_router(translate.router, prefix="/api", tags=["Translate"])
app.include_router(ocr.router, prefix="/api", tags=["OCR"])


@app.get("/")
async def root():
    return {"message": "Anime Transformer API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "ocr_loaded": ocr_service is not None}


def get_ocr_service() -> OCRService:
    """OCR 서비스 인스턴스 반환"""
    return ocr_service
```

### 2.4 config.py - 설정

```python
# app/config.py

from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True

    # 경로 설정
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "uploads")
    OUTPUT_DIR: str = os.path.join(BASE_DIR, "outputs")
    FONT_DIR: str = os.path.join(BASE_DIR, "fonts")

    # 폰트 설정
    DEFAULT_FONT: str = "NanumGothic.ttf"

    # API 설정
    API_SECRET_KEY: Optional[str] = None
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB

    # Claude CLI 설정
    CLAUDE_TIMEOUT: int = 60  # 초

    # Frontend URL (CORS용)
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


settings = Settings()
```

### 2.5 schemas.py - Pydantic 모델

```python
# app/models/schemas.py

from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class TextType(str, Enum):
    DIALOGUE = "dialogue"
    SFX = "sfx"
    NARRATION = "narration"


class TranslateStyle(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    MANGA = "manga"


class Region(BaseModel):
    x: int
    y: int
    width: int
    height: int


class TextItem(BaseModel):
    original: str
    translated: str
    location: str
    type: TextType = TextType.DIALOGUE
    region: Optional[Region] = None


class TranslateRequest(BaseModel):
    text: str
    source_language: str = "일본어"
    target_language: str = "한국어"
    style: TranslateStyle = TranslateStyle.MANGA
    context: Optional[str] = None


class TranslateResponse(BaseModel):
    success: bool
    translation: Optional[str] = None
    error: Optional[str] = None


class BatchTranslateRequest(BaseModel):
    texts: List[str]
    target_language: str = "한국어"
    style: TranslateStyle = TranslateStyle.MANGA


class BatchTranslateResponse(BaseModel):
    success: bool
    translations: Optional[List[str]] = None
    error: Optional[str] = None


class OCRResponse(BaseModel):
    success: bool
    text: Optional[str] = None
    error: Optional[str] = None


class ProcessResponse(BaseModel):
    success: bool
    job_id: str
    texts: Optional[List[TextItem]] = None
    output_url: Optional[str] = None
    error: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int
    current_step: Optional[str] = None
    error: Optional[str] = None
```

### 2.6 OCR Service

```python
# app/services/ocr_service.py

from manga_ocr import MangaOcr
from PIL import Image
from typing import List, Optional
import numpy as np

from app.models.schemas import Region


class OCRService:
    """manga-ocr 래퍼 서비스"""

    def __init__(self):
        """OCR 모델 초기화 (시간이 걸림)"""
        self.model = MangaOcr()

    def extract_text(self, image_path: str) -> str:
        """
        이미지 전체에서 텍스트 추출

        Args:
            image_path: 이미지 파일 경로

        Returns:
            추출된 텍스트
        """
        img = Image.open(image_path)
        text = self.model(img)
        return text

    def extract_from_pil(self, image: Image.Image) -> str:
        """
        PIL Image에서 텍스트 추출

        Args:
            image: PIL Image 객체

        Returns:
            추출된 텍스트
        """
        return self.model(image)

    def extract_from_regions(
        self,
        image_path: str,
        regions: List[Region]
    ) -> List[dict]:
        """
        이미지의 특정 영역들에서 텍스트 추출

        Args:
            image_path: 이미지 파일 경로
            regions: 추출할 영역 리스트

        Returns:
            [{"region": Region, "text": str}, ...]
        """
        img = Image.open(image_path)
        results = []

        for region in regions:
            # 영역 크롭
            cropped = img.crop((
                region.x,
                region.y,
                region.x + region.width,
                region.y + region.height
            ))

            # OCR
            text = self.model(cropped)

            results.append({
                "region": region,
                "text": text
            })

        return results
```

### 2.7 Translate Service (Claude CLI)

```python
# app/services/translate_service.py

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
            {"texts": [{"original": ..., "translated": ..., "location": ..., "type": ...}]}
        """
        prompt = f"""{image_path} 파일을 읽고 분석해줘:

1. 이미지에서 모든 텍스트(대사, 효과음, 나레이션)를 찾아서 추출해줘
2. 각 텍스트의 위치를 설명해줘 (예: 상단 왼쪽 말풍선)
3. 추출한 텍스트를 {target_language}로 번역해줘

다음 JSON 형식으로만 출력해줘:
{{"texts": [{{"original": "원본", "translated": "번역", "location": "위치", "type": "dialogue|sfx|narration"}}]}}"""

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
```

### 2.8 Inpaint Service

```python
# app/services/inpaint_service.py

import cv2
import numpy as np
from PIL import Image
from typing import List
import os

from app.models.schemas import Region


class InpaintService:
    """텍스트 제거 (인페인팅) 서비스"""

    def create_mask(
        self,
        image_path: str,
        regions: List[Region],
        padding: int = 5
    ) -> np.ndarray:
        """
        텍스트 영역 마스크 생성

        Args:
            image_path: 이미지 경로
            regions: 마스킹할 영역들
            padding: 영역 패딩

        Returns:
            마스크 이미지 (numpy array)
        """
        img = cv2.imread(image_path)
        mask = np.zeros(img.shape[:2], dtype=np.uint8)

        for region in regions:
            x, y = region.x, region.y
            w, h = region.width, region.height

            # 패딩 적용
            x1 = max(0, x - padding)
            y1 = max(0, y - padding)
            x2 = min(img.shape[1], x + w + padding)
            y2 = min(img.shape[0], y + h + padding)

            cv2.rectangle(mask, (x1, y1), (x2, y2), 255, -1)

        return mask

    def inpaint_opencv(
        self,
        image_path: str,
        regions: List[Region],
        output_path: str,
        method: str = "telea"
    ) -> str:
        """
        OpenCV 인페인팅으로 텍스트 제거

        Args:
            image_path: 입력 이미지 경로
            regions: 제거할 영역들
            output_path: 출력 이미지 경로
            method: "telea" 또는 "ns"

        Returns:
            출력 파일 경로
        """
        img = cv2.imread(image_path)
        mask = self.create_mask(image_path, regions)

        # 인페인팅 방법 선택
        if method == "telea":
            result = cv2.inpaint(img, mask, 3, cv2.INPAINT_TELEA)
        else:
            result = cv2.inpaint(img, mask, 3, cv2.INPAINT_NS)

        cv2.imwrite(output_path, result)
        return output_path

    def inpaint_simple(
        self,
        image_path: str,
        regions: List[Region],
        output_path: str,
        fill_color: tuple = (255, 255, 255)
    ) -> str:
        """
        단순 색상 채우기 (말풍선용)

        Args:
            image_path: 입력 이미지 경로
            regions: 채울 영역들
            output_path: 출력 이미지 경로
            fill_color: 채울 색상 (BGR)

        Returns:
            출력 파일 경로
        """
        img = cv2.imread(image_path)

        for region in regions:
            x, y = region.x, region.y
            w, h = region.width, region.height

            # 사각형 영역을 색상으로 채움
            cv2.rectangle(img, (x, y), (x + w, y + h), fill_color, -1)

        cv2.imwrite(output_path, result)
        return output_path


# 싱글톤 인스턴스
inpaint_service = InpaintService()
```

### 2.9 Render Service

```python
# app/services/render_service.py

from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional, Tuple
import textwrap
import os

from app.config import settings
from app.models.schemas import Region


class RenderService:
    """텍스트 렌더링 서비스"""

    def __init__(self):
        self.default_font_path = os.path.join(
            settings.FONT_DIR,
            settings.DEFAULT_FONT
        )

    def get_font(
        self,
        size: int,
        font_path: Optional[str] = None
    ) -> ImageFont.FreeTypeFont:
        """
        폰트 로드

        Args:
            size: 폰트 크기
            font_path: 폰트 파일 경로

        Returns:
            ImageFont 객체
        """
        path = font_path or self.default_font_path

        # 기본 폰트 경로들 시도
        font_paths = [
            path,
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # macOS
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Linux
            "C:\\Windows\\Fonts\\malgun.ttf",  # Windows
        ]

        for fp in font_paths:
            if os.path.exists(fp):
                try:
                    return ImageFont.truetype(fp, size)
                except:
                    continue

        # 폴백: 기본 폰트
        return ImageFont.load_default()

    def calculate_font_size(
        self,
        text: str,
        region: Region,
        max_size: int = 30,
        min_size: int = 10
    ) -> int:
        """
        영역에 맞는 폰트 크기 계산

        Args:
            text: 렌더링할 텍스트
            region: 대상 영역
            max_size: 최대 폰트 크기
            min_size: 최소 폰트 크기

        Returns:
            적절한 폰트 크기
        """
        for size in range(max_size, min_size - 1, -1):
            font = self.get_font(size)

            # 글자당 평균 너비 추정
            avg_char_width = size * 0.6
            chars_per_line = max(1, int(region.width / avg_char_width))

            # 텍스트 줄바꿈
            wrapped = textwrap.fill(text, width=chars_per_line)
            lines = wrapped.split('\n')

            # 높이 계산
            text_height = len(lines) * size * 1.2
            text_width = max(len(line) for line in lines) * avg_char_width

            if text_height <= region.height and text_width <= region.width:
                return size

        return min_size

    def render_text(
        self,
        image_path: str,
        texts: List[dict],
        output_path: str,
        font_path: Optional[str] = None
    ) -> str:
        """
        이미지에 텍스트 렌더링

        Args:
            image_path: 입력 이미지 경로
            texts: [{"text": str, "region": Region, "color": str}, ...]
            output_path: 출력 이미지 경로
            font_path: 폰트 파일 경로

        Returns:
            출력 파일 경로
        """
        img = Image.open(image_path)
        draw = ImageDraw.Draw(img)

        for item in texts:
            text = item["text"]
            region = item["region"]
            color = item.get("color", "black")

            # 폰트 크기 계산
            font_size = self.calculate_font_size(text, region)
            font = self.get_font(font_size, font_path)

            # 텍스트 줄바꿈
            avg_char_width = font_size * 0.6
            chars_per_line = max(1, int(region.width / avg_char_width))
            wrapped_text = textwrap.fill(text, width=chars_per_line)

            # 텍스트 크기 계산
            bbox = draw.textbbox((0, 0), wrapped_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            # 중앙 정렬
            x = region.x + (region.width - text_width) // 2
            y = region.y + (region.height - text_height) // 2

            # 외곽선 효과 (가독성 향상)
            outline_color = "white" if color == "black" else "black"
            for dx, dy in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                draw.text((x + dx, y + dy), wrapped_text, font=font, fill=outline_color)

            # 본문 텍스트
            draw.text((x, y), wrapped_text, font=font, fill=color)

        img.save(output_path)
        return output_path


# 싱글톤 인스턴스
render_service = RenderService()
```

### 2.10 Process Router (전체 파이프라인)

```python
# app/routers/process.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import FileResponse
import os
import uuid
import aiofiles

from app.config import settings
from app.models.schemas import ProcessResponse, TextItem, Region
from app.services.ocr_service import OCRService
from app.services.translate_service import translate_service
from app.services.inpaint_service import inpaint_service
from app.services.render_service import render_service
from app.main import get_ocr_service

router = APIRouter()


@router.post("/process", response_model=ProcessResponse)
async def process_image(
    image: UploadFile = File(...),
    target_language: str = Form(default="한국어"),
    style: str = Form(default="manga"),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """
    만화 이미지 전체 처리 파이프라인

    1. 이미지 저장
    2. OCR로 텍스트 추출
    3. Claude로 번역
    4. 텍스트 제거 (인페인팅)
    5. 번역된 텍스트 렌더링
    """
    # 작업 ID 생성
    job_id = str(uuid.uuid4())

    # 디렉토리 생성
    job_upload_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    job_output_dir = os.path.join(settings.OUTPUT_DIR, job_id)
    os.makedirs(job_upload_dir, exist_ok=True)
    os.makedirs(job_output_dir, exist_ok=True)

    try:
        # 1. 이미지 저장
        file_ext = os.path.splitext(image.filename)[1] or ".png"
        input_path = os.path.join(job_upload_dir, f"input{file_ext}")

        async with aiofiles.open(input_path, 'wb') as f:
            content = await image.read()
            await f.write(content)

        # 2. Claude Vision으로 분석 및 번역 (OCR + 번역 통합)
        analysis = await translate_service.analyze_and_translate_image(
            input_path,
            target_language
        )

        texts = []
        if "texts" in analysis:
            for item in analysis["texts"]:
                texts.append(TextItem(
                    original=item.get("original", ""),
                    translated=item.get("translated", ""),
                    location=item.get("location", ""),
                    type=item.get("type", "dialogue")
                ))

        # 3. 인페인팅 (텍스트 제거) - 영역 정보가 있는 경우
        inpainted_path = os.path.join(job_output_dir, "inpainted.png")

        # 간단 버전: 원본 이미지 복사 (실제로는 인페인팅 필요)
        # TODO: 텍스트 영역 감지 후 인페인팅
        import shutil
        shutil.copy(input_path, inpainted_path)

        # 4. 번역된 텍스트 렌더링
        # TODO: 영역 좌표 기반 렌더링
        final_path = os.path.join(job_output_dir, "final.png")
        shutil.copy(inpainted_path, final_path)

        # 결과 URL 생성
        output_url = f"/outputs/{job_id}/final.png"

        return ProcessResponse(
            success=True,
            job_id=job_id,
            texts=texts,
            output_url=output_url
        )

    except Exception as e:
        return ProcessResponse(
            success=False,
            job_id=job_id,
            error=str(e)
        )


@router.get("/download/{job_id}/{filename}")
async def download_result(job_id: str, filename: str):
    """처리된 이미지 다운로드"""
    file_path = os.path.join(settings.OUTPUT_DIR, job_id, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_path,
        media_type="image/png",
        filename=filename
    )
```

### 2.11 Translate Router

```python
# app/routers/translate.py

from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    TranslateRequest,
    TranslateResponse,
    BatchTranslateRequest,
    BatchTranslateResponse
)
from app.services.translate_service import translate_service

router = APIRouter()


@router.post("/translate", response_model=TranslateResponse)
async def translate_text(request: TranslateRequest):
    """단일 텍스트 번역"""
    try:
        result = await translate_service.translate(
            text=request.text,
            source_language=request.source_language,
            target_language=request.target_language,
            style=request.style,
            context=request.context
        )

        return TranslateResponse(
            success=True,
            translation=result
        )
    except Exception as e:
        return TranslateResponse(
            success=False,
            error=str(e)
        )


@router.post("/translate/batch", response_model=BatchTranslateResponse)
async def translate_batch(request: BatchTranslateRequest):
    """다중 텍스트 일괄 번역"""
    try:
        results = await translate_service.translate_batch(
            texts=request.texts,
            target_language=request.target_language,
            style=request.style
        )

        return BatchTranslateResponse(
            success=True,
            translations=results
        )
    except Exception as e:
        return BatchTranslateResponse(
            success=False,
            error=str(e)
        )
```

### 2.12 OCR Router

```python
# app/routers/ocr.py

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
import os
import uuid
import aiofiles

from app.config import settings
from app.models.schemas import OCRResponse
from app.services.ocr_service import OCRService
from app.main import get_ocr_service

router = APIRouter()


@router.post("/ocr", response_model=OCRResponse)
async def extract_text(
    image: UploadFile = File(...),
    ocr_service: OCRService = Depends(get_ocr_service)
):
    """이미지에서 텍스트 추출 (OCR)"""
    # 임시 파일 저장
    temp_id = str(uuid.uuid4())
    temp_path = os.path.join(settings.UPLOAD_DIR, f"{temp_id}_{image.filename}")

    try:
        async with aiofiles.open(temp_path, 'wb') as f:
            content = await image.read()
            await f.write(content)

        # OCR 실행
        text = ocr_service.extract_text(temp_path)

        return OCRResponse(
            success=True,
            text=text
        )
    except Exception as e:
        return OCRResponse(
            success=False,
            error=str(e)
        )
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)
```

### 2.13 run.py - 실행 스크립트

```python
# run.py

import uvicorn
from app.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
```

---

## 3. Frontend 상세 (Next.js)

### 3.1 프로젝트 구조

```
frontend/
├── app/
│   ├── page.tsx                # 메인 페이지
│   ├── layout.tsx              # 레이아웃
│   └── globals.css             # 글로벌 스타일
├── components/
│   ├── ImageUploader.tsx       # 이미지 업로드
│   ├── ImagePreview.tsx        # 이미지 미리보기
│   ├── TranslationResult.tsx   # 번역 결과
│   └── ProgressBar.tsx         # 진행 상태
├── lib/
│   ├── api-client.ts           # API 클라이언트
│   └── types.ts                # TypeScript 타입
├── package.json
├── next.config.js
├── tailwind.config.js
└── tsconfig.json
```

### 3.2 API Client

```typescript
// lib/api-client.ts

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface TextItem {
  original: string;
  translated: string;
  location: string;
  type: 'dialogue' | 'sfx' | 'narration';
}

export interface ProcessResponse {
  success: boolean;
  job_id: string;
  texts?: TextItem[];
  output_url?: string;
  error?: string;
}

export interface TranslateResponse {
  success: boolean;
  translation?: string;
  error?: string;
}

export async function processImage(
  file: File,
  targetLanguage: string = '한국어',
  style: string = 'manga'
): Promise<ProcessResponse> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('target_language', targetLanguage);
  formData.append('style', style);

  const response = await fetch(`${API_BASE_URL}/api/process`, {
    method: 'POST',
    body: formData,
  });

  return response.json();
}

export async function translateText(
  text: string,
  targetLanguage: string = '한국어'
): Promise<TranslateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      target_language: targetLanguage,
    }),
  });

  return response.json();
}

export function getOutputUrl(outputPath: string): string {
  return `${API_BASE_URL}${outputPath}`;
}
```

### 3.3 Main Page

```typescript
// app/page.tsx

'use client';

import { useState } from 'react';
import ImageUploader from '@/components/ImageUploader';
import ImagePreview from '@/components/ImagePreview';
import TranslationResult from '@/components/TranslationResult';
import { processImage, getOutputUrl, TextItem } from '@/lib/api-client';

export default function Home() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState<{
    texts: TextItem[];
    outputUrl: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setPreviewUrl(URL.createObjectURL(file));
    setResult(null);
    setError(null);
  };

  const handleProcess = async () => {
    if (!selectedFile) return;

    setIsProcessing(true);
    setError(null);

    try {
      const response = await processImage(selectedFile);

      if (response.success) {
        setResult({
          texts: response.texts || [],
          outputUrl: response.output_url ? getOutputUrl(response.output_url) : '',
        });
      } else {
        setError(response.error || '처리 중 오류가 발생했습니다.');
      }
    } catch (err) {
      setError('서버 연결에 실패했습니다.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <main className="min-h-screen p-8 bg-gray-100">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-3xl font-bold text-center mb-8">
          Anime/Manga Translator
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* 왼쪽: 업로드 및 원본 */}
          <div className="space-y-4">
            <ImageUploader onFileSelect={handleFileSelect} />

            {previewUrl && (
              <ImagePreview
                src={previewUrl}
                alt="Original"
                label="원본 이미지"
              />
            )}

            <button
              onClick={handleProcess}
              disabled={!selectedFile || isProcessing}
              className={`w-full py-3 px-4 rounded-lg font-medium ${
                !selectedFile || isProcessing
                  ? 'bg-gray-300 cursor-not-allowed'
                  : 'bg-blue-500 hover:bg-blue-600 text-white'
              }`}
            >
              {isProcessing ? '처리 중...' : '번역 시작'}
            </button>
          </div>

          {/* 오른쪽: 결과 */}
          <div className="space-y-4">
            {error && (
              <div className="p-4 bg-red-100 text-red-700 rounded-lg">
                {error}
              </div>
            )}

            {result && (
              <>
                <ImagePreview
                  src={result.outputUrl}
                  alt="Translated"
                  label="번역된 이미지"
                />

                <TranslationResult texts={result.texts} />

                <a
                  href={result.outputUrl}
                  download="translated.png"
                  className="block w-full py-3 px-4 bg-green-500 hover:bg-green-600 text-white text-center rounded-lg font-medium"
                >
                  다운로드
                </a>
              </>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
```

### 3.4 ImageUploader Component

```typescript
// components/ImageUploader.tsx

'use client';

import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';

interface Props {
  onFileSelect: (file: File) => void;
}

export default function ImageUploader({ onFileSelect }: Props) {
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      onFileSelect(acceptedFiles[0]);
    }
  }, [onFileSelect]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg', '.webp']
    },
    maxFiles: 1,
    maxSize: 10 * 1024 * 1024, // 10MB
  });

  return (
    <div
      {...getRootProps()}
      className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
        isDragActive
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-300 hover:border-gray-400'
      }`}
    >
      <input {...getInputProps()} />
      <div className="text-gray-500">
        {isDragActive ? (
          <p>이미지를 여기에 놓으세요</p>
        ) : (
          <>
            <p className="mb-2">이미지를 드래그하거나 클릭하여 선택</p>
            <p className="text-sm">PNG, JPG, WebP (최대 10MB)</p>
          </>
        )}
      </div>
    </div>
  );
}
```

### 3.5 next.config.js

```javascript
// next.config.js

/** @type {import('next').NextConfig} */
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: 'http',
        hostname: 'localhost',
        port: '8000',
        pathname: '/outputs/**',
      },
    ],
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
};

module.exports = nextConfig;
```

---

## 4. 보안 고려사항

### 4.1 API 인증 (선택적)

```python
# app/dependencies.py

from fastapi import Header, HTTPException
from app.config import settings

async def verify_api_key(x_api_key: str = Header(default=None)):
    if settings.API_SECRET_KEY:
        if x_api_key != settings.API_SECRET_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return True
```

### 4.2 파일 검증

```python
# app/utils/image_utils.py

from PIL import Image
import magic

ALLOWED_TYPES = ['image/png', 'image/jpeg', 'image/webp']
MAX_SIZE = 10 * 1024 * 1024  # 10MB

def validate_image(file_path: str) -> bool:
    # MIME 타입 확인
    mime = magic.from_file(file_path, mime=True)
    if mime not in ALLOWED_TYPES:
        return False

    # 파일 크기 확인
    import os
    if os.path.getsize(file_path) > MAX_SIZE:
        return False

    # 이미지 열기 시도
    try:
        Image.open(file_path).verify()
        return True
    except:
        return False
```
