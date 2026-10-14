"""Image -> PDF conversion helpers (Pillow + PyMuPDF)."""

from __future__ import annotations

import io

import pymupdf
from PIL import Image, ImageOps, UnidentifiedImageError

from .mupdf_lock import serialized

# 画像ページの長辺を A4 長辺 (pt) に合わせる。画像自体は元解像度のまま埋め込む。
A4_LONG_SIDE_PT = 842.0

# PyMuPDF がそのまま埋め込める形式
_PASSTHROUGH_FORMATS = {"JPEG", "PNG"}


class ImageConversionError(ValueError):
    pass


def _normalize_image(data: bytes) -> tuple[bytes, int, int]:
    """Apply EXIF orientation and convert to an embeddable format.

    Returns (image bytes, width px, height px).
    """
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.load()
            fmt = img.format
            orientation = img.getexif().get(0x0112, 1)

            if fmt in _PASSTHROUGH_FORMATS and orientation in (1, None) and img.mode != "P":
                return data, img.width, img.height

            img = ImageOps.exif_transpose(img)
            # GIF 等の複数フレーム画像は先頭フレームのみ使用
            if fmt == "JPEG" and img.mode in ("RGB", "L", "CMYK"):
                out_fmt, save_kwargs = "JPEG", {"quality": 95, "subsampling": 0}
            else:
                if img.mode not in ("RGB", "RGBA", "L", "LA"):
                    img = img.convert("RGBA" if "transparency" in img.info or img.mode in ("P", "PA") else "RGB")
                out_fmt, save_kwargs = "PNG", {"optimize": False}
            buf = io.BytesIO()
            img.save(buf, out_fmt, **save_kwargs)
            return buf.getvalue(), img.width, img.height
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ImageConversionError(f"画像を読み込めませんでした: {exc}") from exc


def image_to_pdf_bytes(data: bytes) -> bytes:
    """Convert a single image to a one-page PDF.

    The page keeps the image aspect ratio and its long side equals the A4 long side,
    so images line up naturally with typical documents when merged.
    """
    img_bytes, width, height = _normalize_image(data)
    if width <= 0 or height <= 0:
        raise ImageConversionError("画像サイズが不正です")
    return _embed_image(img_bytes, width, height)


@serialized
def _embed_image(img_bytes: bytes, width: int, height: int) -> bytes:
    scale = A4_LONG_SIDE_PT / max(width, height)
    page_w, page_h = width * scale, height * scale

    doc = pymupdf.open()
    try:
        page = doc.new_page(width=page_w, height=page_h)
        page.insert_image(page.rect, stream=img_bytes, keep_proportion=True)
        return doc.tobytes(garbage=3, deflate=True)
    except Exception as exc:  # PyMuPDF raises generic RuntimeError on bad data
        raise ImageConversionError(f"画像をPDFに変換できませんでした: {exc}") from exc
    finally:
        doc.close()
