from __future__ import annotations

import os
import secrets
import re
import json
from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from .db import save_users, users
from .security import me, now
from .ui import render

router = APIRouter()
_FIREBASE_CERT_INITIALIZED = False


def _title_words(s: str) -> str:
    parts = [p for p in re.split(r"\s+", (s or "").strip()) if p]
    return " ".join(x[:1].upper() + x[1:].lower() for x in parts)


def _candidate_service_account_paths() -> list[Path]:
    here = Path(__file__).resolve()
    project_root = here.parent.parent
    candidates: list[Path] = []

    # Explicit env path first
    env_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "").strip()
    if env_path:
        candidates.append(Path(env_path))

    # USERPROFILE-based desktop paths
    user_profile = os.getenv("USERPROFILE", "").strip()
    if user_profile:
        candidates.extend((Path(user_profile) / "OneDrive" / "Desktop").glob("*firebase-adminsdk*.json"))
        candidates.extend((Path(user_profile) / "Desktop").glob("*firebase-adminsdk*.json"))

    # Project-root local fallback
    candidates.extend(project_root.glob("*firebase-adminsdk*.json"))

    # Glob fallbacks
    candidates.extend((project_root / "secrets").glob("*firebase-adminsdk*.json"))

    # Deduplicate while preserving order
    seen = set()
    uniq: list[Path] = []
    for p in candidates:
        key = str(p).lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(p)
    return uniq


def _discover_service_account_path() -> tuple[str, list[str]]:
    checked: list[str] = []
    for p in _candidate_service_account_paths():
        checked.append(str(p))
        if p.exists() and p.is_file():
            return str(p), checked
    return "", checked


def _service_account_project_id(path: str) -> str:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return str((payload or {}).get("project_id", "")).strip()
    except Exception:
        return ""


@router.get("/auth")
def auth(request: Request):
    if me(request):
        return RedirectResponse("/dashboard", 303)
    mode = request.query_params.get("mode", "login").strip().lower()
    if mode not in {"login", "register"}:
        mode = "login"
    svc, _ = _discover_service_account_path()
    project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip() or ( _service_account_project_id(svc) if svc else "" )
    firebase_config = {
        "apiKey": os.getenv("FIREBASE_WEB_API_KEY", "").strip(),
        "authDomain": f"{project_id}.firebaseapp.com" if project_id else "",
        "projectId": project_id,
        "storageBucket": f"{project_id}.firebasestorage.app" if project_id else "",
    }
    return render(request, "auth.html", "Auth", error=None, firebase_config=firebase_config, mode=mode)


@router.post("/auth/register")
def register(
    request: Request,
    firstName: str = Form(""),
    lastName: str = Form(""),
    name: str = Form(""),
    email: str = Form(...),
    password: str = Form(...),
):
    # Local register path kept only for backward compatibility.
    # Product flow uses Firebase register from /auth?mode=register.
    return RedirectResponse("/auth?mode=register", 303)


@router.post("/auth/login")
def login(request: Request, email: str = Form(...), password: str = Form(...)):
    # Local login path kept only for backward compatibility.
    # Product flow uses Firebase login from /auth.
    return RedirectResponse("/auth?mode=login", 303)


@router.post("/api/auth/firebase-login")
async def firebase_login(request: Request):
    payload = await request.json()
    token = str(payload.get("idToken", "")).strip()
    first_name_in = str(payload.get("firstName", "")).strip()
    last_name_in = str(payload.get("lastName", "")).strip()
    if not token:
        return JSONResponse({"error": "Missing idToken"}, 400)
    try:
        import firebase_admin
        from firebase_admin import auth as fb_auth
        from firebase_admin import credentials as fb_credentials

        svc, checked_paths = _discover_service_account_path()
        svc_ok = bool(svc and Path(svc).exists())
        if not svc_ok:
            return JSONResponse(
                {
                    "error": "Firebase login failed: service account JSON not found.",
                    "hint": "Set FIREBASE_SERVICE_ACCOUNT_JSON, or place the admin JSON in Desktop/project root.",
                    "checked_paths": checked_paths,
                },
                401,
            )

        project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip() or _service_account_project_id(svc)
        if not project_id:
            return JSONResponse({"error": "Firebase login failed: project_id missing in service account JSON."}, 401)
        opts = {"projectId": project_id}
        global _FIREBASE_CERT_INITIALIZED
        if firebase_admin._apps and not _FIREBASE_CERT_INITIALIZED:
            # Recreate default app so it uses certificate creds instead of ADC.
            firebase_admin.delete_app(firebase_admin.get_app())
        if not firebase_admin._apps:
            firebase_admin.initialize_app(fb_credentials.Certificate(svc), options=opts)
            _FIREBASE_CERT_INITIALIZED = True
        d = fb_auth.verify_id_token(token)
        uid, email, name = str(d.get("uid", "")), str(d.get("email", "")), str(d.get("name") or "Student")
        if not uid:
            return JSONResponse({"error": "Token missing uid"}, 401)
    except Exception as e:
        setup_hint = "Set FIREBASE_SERVICE_ACCOUNT_JSON correctly. Optionally set FIREBASE_PROJECT_ID override."
        return JSONResponse({"error": f"Firebase login failed: {e}", "hint": setup_hint}, 401)

    fn = first_name_in or str((name.split(" ")[0] if name else "")).strip()
    ln = last_name_in or str((" ".join(name.split(" ")[1:]) if name and " " in name else "")).strip()
    fn = _title_words(fn)[:20]
    ln = _title_words(ln)
    full = (f"{fn} {ln}".strip() if (fn or ln) else (name or "Student"))
    rows = users()
    u = next((x for x in rows if x.get("firebase_uid") == uid or (email and x.get("email") == email)), None)
    if not u:
        u = {
            "id": secrets.token_hex(8),
            "firebase_uid": uid,
            "firstName": fn,
            "lastName": ln,
            "name": full,
            "email": email,
            "password": "",
            "theme": "light",
            "bio": "",
            "school": "",
            "grade": "",
            "created_at": now().isoformat(),
        }
        rows.append(u)
    else:
        u["firebase_uid"] = uid
        if email:
            u["email"] = email
        if fn:
            u["firstName"] = fn
        if ln:
            u["lastName"] = ln
        u["name"] = (f"{u.get('firstName','')} {u.get('lastName','')}".strip() or u.get("name") or "Student")
    save_users(rows)
    request.session["user_id"] = u["id"]
    return {"ok": True, "user": {"id": u["id"], "name": u["name"], "email": u["email"]}}


@router.get("/api/auth/me")
def auth_me(request: Request):
    u = me(request)
    if not u:
        return JSONResponse({"authenticated": False}, 401)
    return {"authenticated": True, "user": {"id": u["id"], "name": u["name"], "email": u.get("email", "")}}


@router.post("/api/auth/logout")
def auth_logout(request: Request):
    request.session.clear()
    return {"ok": True}


@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", 303)
