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
    try:
        ocr_service = OCRService()
        print("OCR model loaded!")
    except Exception as e:
        print(f"Failed to load OCR model: {e}")
        print("OCR functionality will be disabled.")

    # 디렉토리 생성
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.OUTPUT_DIR, exist_ok=True)

    # OCR 서비스를 라우터에 주입
    ocr.set_ocr_service(ocr_service)

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
        "http://localhost:3000",       # Next.js 개발 서버
        "http://127.0.0.1:3000",
        "http://58.227.107.5:10112",   # 외부 접속
        settings.FRONTEND_URL,          # 프로덕션 URL
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙
os.makedirs(settings.OUTPUT_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=settings.OUTPUT_DIR), name="outputs")
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

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
