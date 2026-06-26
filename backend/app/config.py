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

    # CORS 허용 origin (쉼표 구분, .env로 오버라이드 — IP 하드코딩 금지)
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # SMTP 이메일 알림 (.env로 주입 — 비번은 Gmail 앱 비밀번호)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    SMTP_TO: str = ""
    PUBLIC_URL: str = "https://manga-trans.pgchae.my"

    class Config:
        env_file = ".env"


settings = Settings()
