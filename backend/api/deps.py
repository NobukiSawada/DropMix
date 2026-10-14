"""Shared helpers for the API routers."""

from __future__ import annotations

from pathlib import Path

from fastapi import HTTPException, Request

from ..schemas import PagesRequest
from ..services.pdf_ops import PageRef
from ..workspace import NotFoundError, Workspace


def get_workspace(request: Request) -> Workspace:
    return request.app.state.workspace


def resolve_pages(ws: Workspace, body: PagesRequest) -> list[PageRef]:
    refs: list[PageRef] = []
    for spec in body.pages:
        try:
            f = ws.get_file(spec.file_id)
        except NotFoundError:
            raise HTTPException(404, "ファイルが見つかりません。もう一度追加してください。") from None
        if f.locked:
            raise HTTPException(400, f"「{f.name}」はパスワードで保護されています。先にロックを解除してください。")
        if spec.index >= len(f.pages):
            raise HTTPException(400, f"「{f.name}」に存在しないページが指定されました")
        refs.append(PageRef(path=f.pdf, index=spec.index, rotation=spec.rotation))
    return refs


_KNOWN_EXTS = (".pdf", ".zip", ".jpg", ".jpeg", ".png")


def output_stem(ws: Workspace, body: PagesRequest, suffix: str = "") -> str:
    """File name stem for outputs: the user supplied name, or first file name + suffix."""
    if body.output_name and body.output_name.strip():
        name = body.output_name.strip()
        if name.lower().endswith(_KNOWN_EXTS):
            name = name.rsplit(".", 1)[0]
        return name or "dropmix"
    try:
        stem = Path(ws.get_file(body.pages[0].file_id).name).stem
    except NotFoundError:
        stem = ""
    return (stem or "dropmix") + suffix
