from __future__ import annotations

import os

try:
    import pandas as pd
except Exception:
    pd = None

try:
    from openai import OpenAI
except Exception:
    OpenAI = None

APP_NAME = "JoYuLy Study Hub"

ai = OpenAI() if (OpenAI and os.getenv("OPENAI_API_KEY")) else None


def ensure_storage() -> None:
    # Data now lives in Firebase (Firestore + Storage).
    # Keep this function as a no-op so existing imports do not break.
    return None
