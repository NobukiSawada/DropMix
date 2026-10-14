"""FastAPI application factory."""

from __future__ import annotations

import hmac
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import __version__
from .api import files, tools
from .config import frontend_dist_dir, settings
from .workspace import Workspace

TOKEN_HEADER = "X-DropMix-Token"


def create_app(workspace: Workspace | None = None, token: str | None = None, static_dir: Path | None = None) -> FastAPI:
    """Create the API app.

    token:      when set, every ``/api`` request must carry it (header or ``?token=``).
                This prevents other local programs / web pages from using the API.
    static_dir: built frontend to serve at ``/`` (defaults to ``frontend/dist``).
    """
    owns_workspace = workspace is None
    ws = workspace or Workspace()
    token = token if token is not None else settings.token

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        yield
        if owns_workspace:
            ws.cleanup()

    app = FastAPI(title="DropMix API", version=__version__, lifespan=lifespan, docs_url="/api/docs", redoc_url=None)
    app.state.workspace = ws

    @app.middleware("http")
    async def check_token(request: Request, call_next):
        if token and request.url.path.startswith("/api"):
            supplied = request.headers.get(TOKEN_HEADER) or request.query_params.get("token") or ""
            if not hmac.compare_digest(supplied, token):
                return JSONResponse({"detail": "認証に失敗しました"}, status_code=403)
        return await call_next(request)

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__}

    app.include_router(files.router)
    app.include_router(tools.router)

    dist = static_dir or frontend_dist_dir()
    index = dist / "index.html"
    if index.is_file():
        app.mount("/assets", StaticFiles(directory=dist / "assets", check_dir=False), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            # 静的ファイル (favicon 等) があれば返し、それ以外は index.html を返す
            candidate = (dist / path).resolve()
            if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
                return FileResponse(candidate)
            if path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            return FileResponse(index, headers={"Cache-Control": "no-cache"})

    return app
