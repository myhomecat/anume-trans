"""SMTP 이메일 알림 (Gmail 앱 비밀번호 사용). 작업 완료 시 1통."""
import smtplib
import ssl
from email.message import EmailMessage
from app.config import settings


def configured() -> bool:
    return bool(settings.SMTP_USER and settings.SMTP_PASS and settings.SMTP_TO)


def send_email(subject: str, body: str, to: str = None) -> bool:
    if not configured():
        print("[email] 미설정 (SMTP_USER/PASS/TO 비어있음) — 발송 생략")
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to or settings.SMTP_TO
    msg.set_content(body)
    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=ctx) as srv:
            srv.login(settings.SMTP_USER, settings.SMTP_PASS)
            srv.send_message(msg)
        print(f"[email] sent OK -> {msg['To']}")
        return True
    except Exception as e:
        print(f"[email] send fail: {e}")
        return False
