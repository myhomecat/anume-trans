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
    original_url: Optional[str] = None  # 원본 이미지 URL
    output_url: Optional[str] = None    # 렌더링된 이미지 URL (선택적)
    image_width: Optional[int] = None   # 이미지 너비
    image_height: Optional[int] = None  # 이미지 높이
    error: Optional[str] = None


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    progress: int
    current_step: Optional[str] = None
    error: Optional[str] = None
