"""Runtime settings shared by the API and the desktop launcher."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

# 1 ファイルあたりのアップロード上限 (バイト)
MAX_UPLOAD_BYTES = 500 * 1024 * 1024

PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tif", ".tiff"}


def resource_root() -> Path:
    """Directory that holds bundled resources (PyInstaller aware)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def frontend_dist_dir() -> Path:
    """Location of the built React app (``frontend/dist``)."""
    root = resource_root()
    bundled = root / "frontend_dist"
    if bundled.is_dir():
        return bundled
    return root / "frontend" / "dist"


@dataclass
class Settings:
    # API アクセス用トークン。None の場合は検証しない (開発時)。
    token: str | None = field(default_factory=lambda: os.environ.get("DROPMIX_TOKEN") or None)


settings = Settings()
