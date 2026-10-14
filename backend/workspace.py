"""Temporary on-disk workspace that holds uploaded files and generated outputs.

Everything lives in a private temp directory that is removed when the app exits.
"""

from __future__ import annotations

import io
import shutil
import tempfile
import threading
import time
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from .config import IMAGE_EXTENSIONS, PDF_EXTENSIONS
from .services import pdf_ops
from .services.images import image_to_pdf_bytes

# 保持する出力の最大数 (古いものから削除)
MAX_OUTPUTS = 20
WORKSPACE_PREFIX = "dropmix-"


class WorkspaceError(ValueError):
    pass


class NotFoundError(KeyError):
    pass


@dataclass
class StoredFile:
    id: str
    name: str
    kind: str  # "pdf" | "image"
    size: int
    dir: Path
    source: Path
    pdf: Path  # PDF used for rendering/processing (converted / decrypted)
    locked: bool = False
    pages: list[tuple[float, float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "size": self.size,
            "locked": self.locked,
            "page_count": len(self.pages),
            "pages": [{"width": w, "height": h} for w, h in self.pages],
        }


@dataclass
class StoredOutput:
    id: str
    dir: Path
    files: list[str]

    @property
    def download_name(self) -> str:
        if len(self.files) == 1:
            return self.files[0]
        return Path(self.files[0]).stem.rsplit("_", 1)[0] + ".zip"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "files": self.files,
            "download_name": self.download_name,
            "total_size": sum((self.dir / f).stat().st_size for f in self.files),
        }


def safe_filename(name: str) -> str:
    name = Path(name.replace("\\", "/")).name
    for ch in '<>:"/\\|?*':
        name = name.replace(ch, "_")
    name = "".join(c for c in name if c >= " ").strip(" .")
    return name or "file"


class Workspace:
    def __init__(self, root: Path | None = None) -> None:
        self.root = Path(root) if root else Path(tempfile.mkdtemp(prefix=WORKSPACE_PREFIX))
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "files").mkdir(exist_ok=True)
        (self.root / "outputs").mkdir(exist_ok=True)
        self._files: dict[str, StoredFile] = {}
        self._outputs: dict[str, StoredOutput] = {}
        self._lock = threading.RLock()

    # -- files ---------------------------------------------------------------

    def new_file_dir(self) -> tuple[str, Path]:
        file_id = uuid.uuid4().hex
        d = self.root / "files" / file_id
        d.mkdir(parents=True)
        return file_id, d

    def register_file(self, file_id: str, d: Path, name: str, source: Path) -> StoredFile:
        """Inspect / convert an uploaded file that was written to ``source``."""
        name = safe_filename(name)
        ext = Path(name).suffix.lower()
        try:
            if ext in PDF_EXTENSIONS:
                kind = "pdf"
                pdf = source
                locked, pages = pdf_ops.inspect_pdf(source)
            elif ext in IMAGE_EXTENSIONS:
                kind = "image"
                pdf = d / "image.pdf"
                pdf.write_bytes(image_to_pdf_bytes(source.read_bytes()))
                locked, pages = pdf_ops.inspect_pdf(pdf)
            else:
                raise WorkspaceError(f"未対応のファイル形式です: {name}")
        except Exception:
            shutil.rmtree(d, ignore_errors=True)
            raise

        stored = StoredFile(
            id=file_id,
            name=name,
            kind=kind,
            size=source.stat().st_size,
            dir=d,
            source=source,
            pdf=pdf,
            locked=locked,
            pages=pages,
        )
        with self._lock:
            self._files[file_id] = stored
        return stored

    def get_file(self, file_id: str) -> StoredFile:
        with self._lock:
            f = self._files.get(file_id)
        if f is None:
            raise NotFoundError(file_id)
        return f

    def list_files(self) -> list[StoredFile]:
        with self._lock:
            return list(self._files.values())

    def unlock_file(self, file_id: str, password: str) -> StoredFile:
        f = self.get_file(file_id)
        if not f.locked:
            return f
        dest = f.dir / "unlocked.pdf"
        pdf_ops.decrypt_to(f.source, password, dest)
        locked, pages = pdf_ops.inspect_pdf(dest)
        if locked:
            raise WorkspaceError("PDFのロックを解除できませんでした")
        with self._lock:
            f.pdf, f.locked, f.pages = dest, False, pages
        return f

    def remove_file(self, file_id: str) -> None:
        with self._lock:
            f = self._files.pop(file_id, None)
        if f is None:
            raise NotFoundError(file_id)
        shutil.rmtree(f.dir, ignore_errors=True)

    def clear_files(self) -> None:
        with self._lock:
            files = list(self._files.values())
            self._files.clear()
        for f in files:
            shutil.rmtree(f.dir, ignore_errors=True)

    def thumbnail(self, file_id: str, index: int, width: int) -> Path:
        f = self.get_file(file_id)
        if f.locked:
            raise WorkspaceError("パスワードで保護されたPDFです")
        if not 0 <= index < len(f.pages):
            raise NotFoundError(f"{file_id}:{index}")
        thumbs = f.dir / "thumbs"
        thumbs.mkdir(exist_ok=True)
        path = thumbs / f"{index}_{width}.jpg"
        if not path.exists():
            data = pdf_ops.render_thumbnail(f.pdf, index, width)
            tmp = path.with_suffix(f".{uuid.uuid4().hex}.tmp")
            tmp.write_bytes(data)
            try:
                tmp.replace(path)
            except OSError:
                # Windows では配信中のファイルを置き換えられない。別スレッドが先に
                # 作成済みなので、こちらの一時ファイルは捨てる。
                tmp.unlink(missing_ok=True)
                if not path.exists():
                    raise
        return path

    # -- outputs -------------------------------------------------------------

    def create_output(self, files: list[tuple[str, bytes]]) -> StoredOutput:
        if not files:
            raise WorkspaceError("出力するファイルがありません")
        out_id = uuid.uuid4().hex
        d = self.root / "outputs" / out_id
        d.mkdir(parents=True)
        names: list[str] = []
        used: set[str] = set()
        for name, data in files:
            name = safe_filename(name)
            stem, suffix = Path(name).stem, Path(name).suffix
            candidate, n = name, 2
            while candidate.lower() in used:
                candidate = f"{stem}({n}){suffix}"
                n += 1
            used.add(candidate.lower())
            (d / candidate).write_bytes(data)
            names.append(candidate)
        out = StoredOutput(id=out_id, dir=d, files=names)
        with self._lock:
            self._outputs[out_id] = out
            stale = list(self._outputs)[:-MAX_OUTPUTS]
            removed = [self._outputs.pop(k) for k in stale]
        for o in removed:
            shutil.rmtree(o.dir, ignore_errors=True)
        return out

    def get_output(self, output_id: str) -> StoredOutput:
        with self._lock:
            o = self._outputs.get(output_id)
        if o is None:
            raise NotFoundError(output_id)
        return o

    def output_zip_bytes(self, output: StoredOutput) -> bytes:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for name in output.files:
                zf.write(output.dir / name, arcname=name)
        return buf.getvalue()

    def save_output_to(self, output_id: str, target: Path) -> list[Path]:
        """Copy an output to ``target``.

        Single file outputs: ``target`` is the destination file path.
        Multi file outputs:  ``target`` is a directory.
        """
        o = self.get_output(output_id)
        if len(o.files) == 1:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(o.dir / o.files[0], target)
            return [target]
        target.mkdir(parents=True, exist_ok=True)
        written: list[Path] = []
        for name in o.files:
            dest = target / name
            stem, suffix, n = dest.stem, dest.suffix, 2
            while dest.exists():
                dest = target / f"{stem}({n}){suffix}"
                n += 1
            shutil.copyfile(o.dir / name, dest)
            written.append(dest)
        return written

    # -- lifecycle -------------------------------------------------------------

    def cleanup(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)


def purge_stale_workspaces(max_age_hours: float = 24) -> int:
    """Remove workspaces left behind by crashed / force-killed sessions."""
    cutoff = time.time() - max_age_hours * 3600
    removed = 0
    for d in Path(tempfile.gettempdir()).glob(f"{WORKSPACE_PREFIX}*"):
        try:
            if not d.is_dir():
                continue
            # 使用中のワークスペースはファイル追加・出力のたびに更新される
            last_used = max(p.stat().st_mtime for p in (d, d / "files", d / "outputs") if p.exists())
            if last_used < cutoff:
                shutil.rmtree(d, ignore_errors=True)
                removed += 1
        except OSError:
            pass
    return removed
