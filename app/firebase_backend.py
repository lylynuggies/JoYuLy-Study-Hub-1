from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_APP_READY = False
_DB = None
_BUCKET = None


def _candidate_service_account_paths() -> list[Path]:
    here = Path(__file__).resolve()
    project_root = here.parent.parent
    user_profile = os.getenv("USERPROFILE", "").strip()
    out = []
    env = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if env:
        out.append(Path(env))
    if user_profile:
        out.extend((Path(user_profile) / "OneDrive" / "Desktop").glob("*firebase-adminsdk*.json"))
        out.extend((Path(user_profile) / "Desktop").glob("*firebase-adminsdk*.json"))
    out.extend(project_root.glob("*firebase-adminsdk*.json"))
    out.extend((project_root / "secrets").glob("*firebase-adminsdk*.json"))
    seen = set()
    uniq = []
    for p in out:
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def _discover_service_account_path() -> str:
    for p in _candidate_service_account_paths():
        if p.exists() and p.is_file():
            return str(p)
    return ""


def ensure_firebase() -> None:
    global _APP_READY, _DB, _BUCKET
    if _APP_READY:
        return
    import firebase_admin
    from firebase_admin import credentials, firestore, storage

    svc = _discover_service_account_path()
    if not svc:
        raise RuntimeError("Firebase Admin service account JSON not found.")
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    bucket_name = os.getenv("FIREBASE_STORAGE_BUCKET", "").strip()
    if not project_id:
        raise RuntimeError("FIREBASE_PROJECT_ID is not set.")
    if not bucket_name:
        raise RuntimeError("FIREBASE_STORAGE_BUCKET is not set.")
    if firebase_admin._apps:
        app = firebase_admin.get_app()
    else:
        app = firebase_admin.initialize_app(
            credentials.Certificate(svc),
            options={"projectId": project_id, "storageBucket": bucket_name},
        )
    _DB = firestore.client(app=app)
    _BUCKET = storage.bucket(app=app)
    _APP_READY = True


def db():
    ensure_firebase()
    return _DB


def bucket():
    ensure_firebase()
    return _BUCKET


def upload_bytes(blob_path: str, data: bytes, content_type: str | None = None) -> str:
    b = bucket().blob(blob_path)
    b.upload_from_string(data, content_type=content_type)
    return blob_path


def download_bytes(blob_path: str) -> bytes:
    b = bucket().blob(blob_path)
    if not b.exists():
        raise FileNotFoundError(blob_path)
    return b.download_as_bytes()


def delete_blob(blob_path: str) -> None:
    b = bucket().blob(blob_path)
    if b.exists():
        b.delete()
