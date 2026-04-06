from fastapi import APIRouter
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
