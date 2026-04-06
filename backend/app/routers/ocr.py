from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import uuid
import aiofiles

from app.config import settings
from app.models.schemas import OCRResponse

router = APIRouter()

# OCR 서비스 인스턴스 (main.py에서 주입됨)
_ocr_service = None


def set_ocr_service(service):
    """OCR 서비스 설정"""
    global _ocr_service
    _ocr_service = service


def get_ocr_service():
    """OCR 서비스 가져오기"""
    return _ocr_service


@router.post("/ocr", response_model=OCRResponse)
async def extract_text(
    image: UploadFile = File(...),
):
    """이미지에서 텍스트 추출 (OCR)"""
    ocr_service = get_ocr_service()

    if ocr_service is None:
        return OCRResponse(
            success=False,
            error="OCR service not initialized"
        )

    # 임시 파일 저장
    temp_id = str(uuid.uuid4())
    temp_path = os.path.join(settings.UPLOAD_DIR, f"{temp_id}_{image.filename}")

    try:
        # 디렉토리 생성
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

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
