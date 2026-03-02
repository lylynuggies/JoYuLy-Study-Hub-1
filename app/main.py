from __future__ import annotations

import os
import secrets
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.types import ASGIApp, Receive, Scope, Send

from .routes_auth import router as auth_router
from .routes_pages import router as pages_router
from .routes_plan import router as plan_router
from .routes_reports import router as reports_router
from .routes_tracker import router as tracker_router
from .state import ensure_storage

BASE = Path(__file__).resolve().parent.parent

_SESSION_STORE: dict[str, dict] = {}


class CookieSessionMiddleware:
    def __init__(self, app: ASGIApp, cookie_name: str = "sid"):
        self.app = app
        self.cookie_name = cookie_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        raw_cookie = headers.get(b"cookie", b"").decode("latin-1")
        cookies = {}
        if raw_cookie:
            for part in raw_cookie.split(";"):
                if "=" in part:
                    k, v = part.split("=", 1)
                    cookies[k.strip()] = v.strip()

        sid = cookies.get(self.cookie_name)
        if not sid or sid not in _SESSION_STORE:
            sid = secrets.token_urlsafe(24)
            _SESSION_STORE[sid] = {}
        session_data = _SESSION_STORE[sid]
        scope["session"] = session_data

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                cookie = f"{self.cookie_name}={sid}; Path=/; HttpOnly; SameSite=Lax"
                headers_list.append((b"set-cookie", cookie.encode("latin-1")))
                message["headers"] = headers_list
            await send(message)

        await self.app(scope, receive, send_wrapper)


def create_app() -> FastAPI:
    ensure_storage()
    app = FastAPI(title="JoYuLy Study Hub")
    app.add_middleware(CookieSessionMiddleware)
    app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
    app.include_router(auth_router)
    app.include_router(pages_router)
    app.include_router(tracker_router)
    app.include_router(reports_router)
    app.include_router(plan_router)
    return app


app = create_app()
