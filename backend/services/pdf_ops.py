"""PDF operations built on PyMuPDF.

All operations work on a *page list*: an ordered list of ``PageRef`` that point to
pages of uploaded documents plus an extra rotation. This lets the UI reorder,
rotate and delete pages freely, and every tool simply consumes the arranged list.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pymupdf

from .mupdf_lock import serialized


class PdfOperationError(ValueError):
    pass


@dataclass(frozen=True)
class PageRef:
    path: Path  # PDF file that contains the page
    index: int  # 0-based page index in that file
    rotation: int = 0  # extra clockwise rotation (multiple of 90)


# ---------------------------------------------------------------------------
# Building documents
# ---------------------------------------------------------------------------


def _group_runs(pages: list[PageRef]) -> Iterable[tuple[Path, int, int]]:
    """Group consecutive pages of the same file into (path, from, to) runs.

    ``insert_pdf`` is much faster for ranges than for single pages.
    """
    start = 0
    for i in range(1, len(pages) + 1):
        if i == len(pages):
            yield pages[start].path, pages[start].index, pages[i - 1].index
            break
        prev, cur = pages[i - 1], pages[i]
        if cur.path != prev.path or cur.index != prev.index + 1:
            yield pages[start].path, pages[start].index, prev.index
            start = i


def build_document(pages: list[PageRef]) -> pymupdf.Document:
    """Assemble a new document from the page list (order + rotation applied)."""
    if not pages:
        raise PdfOperationError("ページが選択されていません")

    out = pymupdf.open()
    sources: dict[Path, pymupdf.Document] = {}
    try:
        for path, first, last in _group_runs(pages):
            src = sources.get(path)
            if src is None:
                src = pymupdf.open(path)
                sources[path] = src
            if not (0 <= first < src.page_count and 0 <= last < src.page_count):
                raise PdfOperationError("存在しないページが指定されました")
            out.insert_pdf(src, from_page=first, to_page=last, annots=True, links=True)
    except PdfOperationError:
        out.close()
        raise
    except Exception as exc:
        out.close()
        raise PdfOperationError(f"PDFの読み込みに失敗しました: {exc}") from exc
    finally:
        for src in sources.values():
            src.close()

    for page, ref in zip(out, pages):
        extra = ref.rotation % 360
        if extra:
            page.set_rotation((page.rotation + extra) % 360)
    return out


def save_bytes(doc: pymupdf.Document, *, compress: bool = True) -> bytes:
    if compress:
        return doc.tobytes(garbage=3, deflate=True, use_objstms=1)
    return doc.tobytes()


# ---------------------------------------------------------------------------
# Page range parsing ("1-3, 5, 8-")
# ---------------------------------------------------------------------------

_RANGE_RE = re.compile(r"^\s*(\d*)\s*(-?)\s*(\d*)\s*$")


def parse_ranges(spec: str, total: int) -> list[list[int]]:
    """Parse a 1-based range spec into lists of 0-based indices.

    Each comma separated part becomes one group. ``"1-3,5,8-"`` with total=10 ->
    ``[[0,1,2],[4],[7,8,9]]``.
    """
    groups: list[list[int]] = []
    normalized = re.sub(r"\s*[-～〜−ー]\s*", "-", spec)  # 「1 - 3」「1〜3」も受け付ける
    parts = [p for p in re.split(r"[,、，\s]+", normalized) if p]
    if not parts:
        raise PdfOperationError("ページ範囲を入力してください (例: 1-3, 5)")
    for part in parts:
        m = _RANGE_RE.match(part)
        if not m or (not m.group(1) and not m.group(3)):
            raise PdfOperationError(f"ページ範囲の書式が正しくありません: {part}")
        a, dash, b = m.groups()
        if dash:
            start = int(a) if a else 1
            end = int(b) if b else total
        else:
            start = end = int(a)
        if start < 1 or end > total or start > end:
            raise PdfOperationError(f"ページ範囲が不正です: {part} (1〜{total})")
        groups.append(list(range(start - 1, end)))
    return groups


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@serialized
def merge(pages: list[PageRef]) -> bytes:
    doc = build_document(pages)
    try:
        return save_bytes(doc)
    finally:
        doc.close()


@serialized
def split(pages: list[PageRef], mode: str, ranges: str | None = None) -> list[tuple[int, int, bytes]]:
    """Split the arranged pages.

    mode="each":    every page becomes its own PDF.
    mode="ranges":  every range group becomes its own PDF.
    mode="extract": all pages in the ranges are extracted into one PDF.

    Returns a list of (first page no, last page no, pdf bytes) with 1-based numbers.
    """
    total = len(pages)
    if total == 0:
        raise PdfOperationError("ページが選択されていません")

    if mode == "each":
        groups = [[i] for i in range(total)]
    elif mode in ("ranges", "extract"):
        groups = parse_ranges(ranges or "", total)
        if mode == "extract":
            groups = [[i for g in groups for i in g]]
    else:
        raise PdfOperationError(f"未知の分割モードです: {mode}")

    results: list[tuple[int, int, bytes]] = []
    for group in groups:
        doc = build_document([pages[i] for i in group])
        try:
            results.append((group[0] + 1, group[-1] + 1, save_bytes(doc)))
        finally:
            doc.close()
    return results


@serialized
def to_images(
    pages: list[PageRef],
    fmt: str = "jpg",
    dpi: int = 200,
    jpg_quality: int = 90,
) -> list[bytes]:
    """Render pages to JPG/PNG. Returns image bytes in page order."""
    if fmt not in ("jpg", "png"):
        raise PdfOperationError("出力形式は jpg または png を指定してください")
    if not 36 <= dpi <= 600:
        raise PdfOperationError("解像度は 36〜600 dpi の範囲で指定してください")
    jpg_quality = max(10, min(100, jpg_quality))

    doc = build_document(pages)
    try:
        images: list[bytes] = []
        for page in doc:
            # JPG は透過を持てないので白背景で描画する
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            images.append(pix.tobytes("jpg", jpg_quality=jpg_quality) if fmt == "jpg" else pix.tobytes("png"))
        return images
    finally:
        doc.close()


COMPRESS_LEVELS = ("standard", "strong", "max")


@serialized
def compress(pages: list[PageRef], level: str = "standard") -> tuple[int, bytes]:
    """Optimize the document. Returns (size before, compressed bytes)."""
    if level not in COMPRESS_LEVELS:
        raise PdfOperationError(f"未知の圧縮レベルです: {level}")
    doc = build_document(pages)
    try:
        before = len(doc.tobytes())
        if level in ("strong", "max") and hasattr(doc, "rewrite_images"):
            dpi_target, quality = (150, 75) if level == "strong" else (96, 55)
            doc.rewrite_images(
                dpi_threshold=dpi_target + 10,
                dpi_target=dpi_target,
                quality=quality,
                lossy=True,
                lossless=True,
                bitonal=False,
                color=True,
                gray=True,
            )
        if level == "max":
            doc.subset_fonts()
            doc.scrub(
                attached_files=False,
                clean_pages=True,
                embedded_files=False,
                hidden_text=False,
                javascript=True,
                metadata=False,
                redactions=False,
                redact_images=0,
                remove_links=False,
                reset_fields=False,
                reset_responses=False,
                thumbnails=True,
                xml_metadata=True,
            )
        data = doc.tobytes(
            garbage=4,
            deflate=True,
            deflate_images=True,
            deflate_fonts=True,
            clean=True,
            use_objstms=1,
        )
        return before, data
    finally:
        doc.close()


# --- Watermark / page numbers ------------------------------------------------


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    m = re.fullmatch(r"#?([0-9a-fA-F]{6})", color.strip())
    if not m:
        raise PdfOperationError(f"色の指定が不正です: {color}")
    v = m.group(1)
    return tuple(int(v[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]


def _font_for(text: str) -> pymupdf.Font:
    # ASCII のみなら埋め込み不要の Helvetica、日本語を含む場合は内蔵 CJK フォント
    # (CJK フォントは保存前に subset_fonts() で使用文字だけに絞る)
    return pymupdf.Font("helv") if text.isascii() else pymupdf.Font("cjk")


def _draw_text(
    page: pymupdf.Page,
    point: pymupdf.Point,
    text: str,
    *,
    font: pymupdf.Font,
    fontsize: float,
    color: tuple[float, float, float],
    opacity: float = 1,
    angle: float = 0,
) -> None:
    """Draw text at *visual* coordinates (as the page is displayed).

    ``angle`` is counter-clockwise in degrees as seen by the user. Page rotation is
    compensated so the result looks the same regardless of ``page.rotation``.
    """
    p = point * page.derotation_matrix
    tw = pymupdf.TextWriter(page.rect)
    tw.append(p, text, font=font, fontsize=fontsize)
    rot = (angle + page.rotation) % 360
    tw.write_text(page, color=color, opacity=opacity, morph=(p, pymupdf.Matrix(rot)) if rot else None)


def _save_with_text(doc: pymupdf.Document, used_cjk: bool) -> bytes:
    if used_cjk:
        doc.subset_fonts()
    return save_bytes(doc)


@serialized
def add_watermark(
    pages: list[PageRef],
    text: str,
    *,
    fontsize: float = 60,
    opacity: float = 0.25,
    angle: float = 45,
    color: str = "#16a34a",
) -> bytes:
    text = text.strip()
    if not text:
        raise PdfOperationError("透かしのテキストを入力してください")
    if not 0.05 <= opacity <= 1:
        raise PdfOperationError("不透明度は 0.05〜1 の範囲で指定してください")
    rgb = _hex_to_rgb(color)
    font = _font_for(text)
    rad = math.radians(angle)
    direction = pymupdf.Point(math.cos(rad), -math.sin(rad))  # 表示座標系 (y 下向き)
    normal = pymupdf.Point(math.sin(rad), math.cos(rad))  # 文字の下方向

    doc = build_document(pages)
    try:
        for page in doc:
            w, h = page.rect.width, page.rect.height
            # 回転後の文字列がページ内に収まるようにフォントサイズを縮める
            size = fontsize
            length = font.text_length(text, fontsize=size)
            fit_w = (w * 0.9) / max(abs(direction.x), 1e-6)
            fit_h = (h * 0.9) / max(abs(direction.y), 1e-6)
            limit = min(fit_w, fit_h)
            if length > limit:
                size *= limit / length
                length = limit
            center = pymupdf.Point(w / 2, h / 2)
            # ベースライン始点 = 中心 - 文字列長/2 (進行方向) + 文字高さの約1/3 (下方向)
            start = center - direction * (length / 2) + normal * (size * 0.35)
            _draw_text(page, start, text, font=font, fontsize=size, color=rgb, opacity=opacity, angle=angle)
        return _save_with_text(doc, not text.isascii())
    finally:
        doc.close()


PAGE_NUMBER_POSITIONS = (
    "bottom-center",
    "bottom-right",
    "bottom-left",
    "top-center",
    "top-right",
    "top-left",
)


@serialized
def add_page_numbers(
    pages: list[PageRef],
    *,
    position: str = "bottom-center",
    fmt: str = "{n} / {total}",
    start: int = 1,
    fontsize: float = 11,
    color: str = "#333333",
    margin: float = 28,
) -> bytes:
    if position not in PAGE_NUMBER_POSITIONS:
        raise PdfOperationError(f"未知の位置です: {position}")
    if "{n}" not in fmt:
        raise PdfOperationError("書式には {n} を含めてください")
    rgb = _hex_to_rgb(color)

    doc = build_document(pages)
    total = doc.page_count + start - 1
    used_cjk = False
    try:
        for i, page in enumerate(doc):
            label = fmt.replace("{n}", str(i + start)).replace("{total}", str(total))
            font = _font_for(label)
            used_cjk |= not label.isascii()
            w, h = page.rect.width, page.rect.height
            width = font.text_length(label, fontsize=fontsize)
            vertical, horizontal = position.split("-")
            y = margin + fontsize * 0.8 if vertical == "top" else h - margin
            if horizontal == "left":
                x = margin
            elif horizontal == "right":
                x = w - margin - width
            else:
                x = (w - width) / 2
            _draw_text(page, pymupdf.Point(x, y), label, font=font, fontsize=fontsize, color=rgb)
        return _save_with_text(doc, used_cjk)
    finally:
        doc.close()


# --- Security ---------------------------------------------------------------


@serialized
def protect(
    pages: list[PageRef],
    user_password: str,
    owner_password: str | None = None,
    *,
    allow_print: bool = True,
    allow_copy: bool = False,
    allow_modify: bool = False,
) -> bytes:
    if not user_password:
        raise PdfOperationError("パスワードを入力してください")
    owner = owner_password or user_password

    perms = pymupdf.PDF_PERM_ACCESSIBILITY
    if allow_print:
        perms |= pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_PRINT_HQ
    if allow_copy:
        perms |= pymupdf.PDF_PERM_COPY
    if allow_modify:
        perms |= pymupdf.PDF_PERM_MODIFY | pymupdf.PDF_PERM_ANNOTATE | pymupdf.PDF_PERM_FORM | pymupdf.PDF_PERM_ASSEMBLE

    doc = build_document(pages)
    try:
        return doc.tobytes(
            garbage=3,
            deflate=True,
            encryption=pymupdf.PDF_ENCRYPT_AES_256,
            user_pw=user_password,
            owner_pw=owner,
            permissions=perms,
        )
    finally:
        doc.close()


@serialized
def inspect_pdf(path: Path) -> tuple[bool, list[tuple[float, float]]]:
    """Return (needs_password, [(width, height)...]) for a PDF file."""
    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        raise PdfOperationError(f"PDFを開けませんでした: {exc}") from exc
    try:
        if not doc.is_pdf:
            raise PdfOperationError("PDFファイルではありません")
        if doc.needs_pass:
            return True, []
        if doc.page_count == 0:
            raise PdfOperationError("ページがないPDFです")
        return False, [(p.rect.width, p.rect.height) for p in doc]
    finally:
        doc.close()


@serialized
def decrypt_to(src: Path, password: str, dest: Path) -> None:
    """Authenticate an encrypted PDF and save a decrypted copy."""
    doc = pymupdf.open(src)
    try:
        if not doc.authenticate(password):
            raise PdfOperationError("パスワードが違います")
        doc.save(dest, encryption=pymupdf.PDF_ENCRYPT_NONE, garbage=1)
    finally:
        doc.close()


@serialized
def render_thumbnail(path: Path, index: int, width: int) -> bytes:
    doc = pymupdf.open(path)
    try:
        if not 0 <= index < doc.page_count:
            raise PdfOperationError("存在しないページです")
        page = doc[index]
        zoom = width / max(page.rect.width, 1)
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("jpg", jpg_quality=82)
    finally:
        doc.close()
