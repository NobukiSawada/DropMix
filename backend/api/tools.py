"""Processing endpoints. Each tool stores its result as an *output* that the
client then downloads (browser) or saves through the native dialog (desktop)."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response

from ..schemas import (
    CompressRequest,
    ImagesRequest,
    MergeRequest,
    PageNumbersRequest,
    ProtectRequest,
    SplitRequest,
    WatermarkRequest,
)
from ..services import pdf_ops
from ..services.pdf_ops import PdfOperationError
from ..workspace import NotFoundError, Workspace, WorkspaceError
from .deps import get_workspace, output_stem, resolve_pages

router = APIRouter(prefix="/api", tags=["tools"])


def _run(fn):
    try:
        return fn()
    except (PdfOperationError, WorkspaceError) as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/merge")
def merge(body: MergeRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    pages = resolve_pages(ws, body)
    data = _run(lambda: pdf_ops.merge(pages))
    suffix = "_merged" if len({p.file_id for p in body.pages}) > 1 else "_edited"
    return ws.create_output([(f"{output_stem(ws, body, suffix)}.pdf", data)]).to_dict()


@router.post("/split")
def split(body: SplitRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    pages = resolve_pages(ws, body)
    parts = _run(lambda: pdf_ops.split(pages, body.mode, body.ranges))
    stem = output_stem(ws, body)
    width = len(str(len(pages)))
    files = []
    for first, last, data in parts:
        label = f"p{first:0{width}d}" if first == last else f"p{first:0{width}d}-{last:0{width}d}"
        if body.mode == "extract":
            label = "extract"
        files.append((f"{stem}_{label}.pdf", data))
    return ws.create_output(files).to_dict()


@router.post("/to-images")
def to_images(body: ImagesRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    pages = resolve_pages(ws, body)
    stem = output_stem(ws, body)
    width = max(2, len(str(len(pages))))

    def render():
        images = pdf_ops.to_images(pages, body.format, body.dpi, body.quality)
        return [(f"{stem}_p{i:0{width}d}.{body.format}", data) for i, data in enumerate(images, start=1)]

    return ws.create_output(_run(render)).to_dict()


def _original_pdf_size(ws: Workspace, body: CompressRequest) -> int | None:
    """Total size of the source PDFs when every page of them is used exactly once."""
    used: dict[str, set[int]] = {}
    for spec in body.pages:
        used.setdefault(spec.file_id, set()).add(spec.index)
    if sum(len(v) for v in used.values()) != len(body.pages):
        return None  # 同じページが重複している
    total = 0
    for file_id, indices in used.items():
        f = ws.get_file(file_id)
        if f.kind != "pdf" or len(indices) != len(f.pages):
            return None
        total += f.size
    return total


@router.post("/compress")
def compress(body: CompressRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    pages = resolve_pages(ws, body)
    assembled, data = _run(lambda: pdf_ops.compress(pages, body.level))
    result = ws.create_output([(f"{output_stem(ws, body, '_compressed')}.pdf", data)]).to_dict()
    # ファイル全体を圧縮した場合は元ファイルのサイズと比較する
    result["size_before"] = _original_pdf_size(ws, body) or assembled
    result["size_after"] = len(data)
    return result


@router.post("/watermark")
def watermark(body: WatermarkRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    pages = resolve_pages(ws, body)
    data = _run(
        lambda: pdf_ops.add_watermark(
            pages,
            body.text,
            fontsize=body.fontsize,
            opacity=body.opacity,
            angle=body.angle,
            color=body.color,
        )
    )
    return ws.create_output([(f"{output_stem(ws, body, '_watermark')}.pdf", data)]).to_dict()


@router.post("/page-numbers")
def page_numbers(body: PageNumbersRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    pages = resolve_pages(ws, body)
    data = _run(
        lambda: pdf_ops.add_page_numbers(
            pages,
            position=body.position,
            fmt=body.format,
            start=body.start,
            fontsize=body.fontsize,
            color=body.color,
        )
    )
    return ws.create_output([(f"{output_stem(ws, body, '_numbered')}.pdf", data)]).to_dict()


@router.post("/protect")
def protect(body: ProtectRequest, ws: Workspace = Depends(get_workspace)) -> dict:
    pages = resolve_pages(ws, body)
    data = _run(
        lambda: pdf_ops.protect(
            pages,
            body.user_password,
            body.owner_password,
            allow_print=body.allow_print,
            allow_copy=body.allow_copy,
            allow_modify=body.allow_modify,
        )
    )
    return ws.create_output([(f"{output_stem(ws, body, '_protected')}.pdf", data)]).to_dict()


@router.get("/outputs/{output_id}/download")
def download_output(output_id: str, ws: Workspace = Depends(get_workspace)):
    try:
        out = ws.get_output(output_id)
    except NotFoundError:
        raise HTTPException(404, "出力ファイルが見つかりません") from None
    if len(out.files) == 1:
        return FileResponse(out.dir / out.files[0], filename=out.files[0])
    return Response(
        ws.output_zip_bytes(out),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(out.download_name)}"},
    )
