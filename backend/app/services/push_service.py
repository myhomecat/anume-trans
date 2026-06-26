"""Web Push (VAPID) 발송 서비스. job 완료 시 브라우저로 푸시."""
import os
import json
from pywebpush import webpush, WebPushException

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # backend/
_PRIV = os.path.join(_BASE, "vapid_private.pem")
_PUB = os.path.join(_BASE, "vapid_public.txt")
VAPID_CLAIMS = {"sub": "mailto:pgchae@mediquitous.com"}

_priv_cache = None


def public_key() -> str:
    try:
        with open(_PUB) as f:
            return f.read().strip()
    except Exception:
        return ""


def _private_pem() -> str:
    global _priv_cache
    if _priv_cache is None:
        with open(_PRIV) as f:
            _priv_cache = f.read()
    return _priv_cache


def send_push(subscription: dict, title: str, body: str, url: str = "/") -> bool:
    try:
        webpush(
            subscription_info=subscription,
            data=json.dumps({"title": title, "body": body, "url": url}),
            vapid_private_key=_private_pem(),
            vapid_claims=dict(VAPID_CLAIMS),
        )
        return True
    except WebPushException as e:
        print(f"[push] send fail: {e}")
        return False
    except Exception as e:
        print(f"[push] error: {e}")
        return False
