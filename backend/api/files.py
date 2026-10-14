"""Upload / inspect / thumbnail endpoints."""

from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from ..config import IMAGE_EXTENSIONS, MAX_UPLOAD_BYTES, PDF_EXTENSIONS
from ..schemas import UnlockRequest
from ..services.images import ImageConversionError
from ..services.pdf_ops import PdfOperationError
from ..workspace import NotFoundError, Workspace, WorkspaceError, safe_filename
from .deps import get_workspace

router = APIRouter(prefix="/api/files", tags=["files"])

_CHUNK = 1024 * 1024


@router.post("")
def upload_file(file: UploadFile = File(...), ws: Workspace = Depends(get_workspace)) -> dict:
    name = safe_filename(file.filename or "file")
    ext = Path(name).suffix.lower()
    if ext not in PDF_EXTENSIONS | IMAGE_EXTENSIONS:
        raise HTTPException(415, f"未対応のファイル形式です: {name}（PDF / JPG / PNG などに対応）")

    file_id, d = ws.new_file_dir()
    source = d / f"source{ext}"
    written = 0
    try:
        with source.open("wb") as out:
            while chunk := file.file.read(_CHUNK):
                written += len(chunk)
                if written > MAX_UPLOAD_BYTES:
                    raise HTTPException(413, f"ファイルが大きすぎます（上限 {MAX_UPLOAD_BYTES // 1024 // 1024}MB）")
                out.write(chunk)
        if written == 0:
            raise HTTPException(400, f"空のファイルです: {name}")
        stored = ws.register_file(file_id, d, name, source)
    except HTTPException:
        shutil.rmtree(d, ignore_errors=True)
        raise
    except (PdfOperationError, ImageConversionError, WorkspaceError) as exc:
        raise HTTPException(400, f"{name}: {exc}") from exc
    return stored.to_dict()


@router.get("")
def list_files(ws: Workspace = Depends(get_workspace)) -> list[dict]:
    return [f.to_dict() for f in ws.list_files()]


@router.delete("")
def clear_files(ws: Workspace = Depends(get_workspace)) -> dict:
    ws.clear_files()
    return {"ok": True}


@router.delete("/{file_id}")
def delete_file(file_id: str, ws: Workspace = Depends(get_workspace)) -> dict:
    try:
        ws.remove_file(file_id)
    except NotFoundError:
        raise HTTPException(404, "ファイルが見つかりません") from None
    return {"ok": True}


@router.post("/{file_id}/unlock")
def unlock_file(file_id: str, body: UnlockRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    try:
        return ws.unlock_file(file_id, body.password).to_dict()
    except NotFoundError:
        raise HTTPException(404, "ファイルが見つかりません") from None
    except (PdfOperationError, WorkspaceError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.get("/{file_id}/pages/{index}/thumbnail")
def thumbnail(
    file_id: str,
    index: int,
    w: int = Query(240, ge=32, le=2000),
    ws: Workspace = Depends(get_workspace),
) -> FileResponse:
    # キャッシュ効率のため幅を 80px 単位に丸める
    width = min(2000, max(80, (w + 79) // 80 * 80))
    try:
        path = ws.thumbnail(file_id, index, width)
    except NotFoundError:
        raise HTTPException(404, "ページが見つかりません") from None
    except (PdfOperationError, WorkspaceError) as exc:
        raise HTTPException(400, str(exc)) from exc
    return FileResponse(path, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=3600"})
