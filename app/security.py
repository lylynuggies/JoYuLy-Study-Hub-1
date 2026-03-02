from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import datetime

from fastapi import Request
from fastapi.responses import RedirectResponse

from .db import users


def now() -> datetime:
    return datetime.utcnow()


def hp(password: str, salt: str | None = None) -> str:
    s = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), s.encode(), 120000).hex()
    return f"{s}${digest}"


def vp(password: str, stored: str) -> bool:
    try:
        s = stored.split("$", 1)[0]
    except Exception:
        return False
    return hmac.compare_digest(hp(password, s), stored)


def slug(value: str) -> str:
    return (re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value.lower())).strip("-") or "item")[:70]


def me(request: Request):
    uid = request.session.get("user_id")
    return next((u for u in users() if u.get("id") == uid), None)


def must(request: Request):
    return me(request) or RedirectResponse("/auth", 303)

