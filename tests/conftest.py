from __future__ import annotations

import io
import sys
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app import create_app  # noqa: E402
from backend.workspace import Workspace  # noqa: E402


def make_pdf(labels: list[str], width: float = 595, height: float = 842, password: str | None = None) -> bytes:
    doc = pymupdf.open()
    for label in labels:
        page = doc.new_page(width=width, height=height)
        page.insert_text((72, 100), label, fontsize=24)
    kwargs = {}
    if password:
        kwargs = dict(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=password, owner_pw=password)
    data = doc.tobytes(**kwargs)
    doc.close()
    return data


def make_image(fmt: str = "PNG", size=(400, 200), color=(0, 160, 80), mode: str = "RGB") -> bytes:
    img = Image.new(mode, size, color)
    buf = io.BytesIO()
    img.save(buf, fmt)
    return buf.getvalue()


def page_texts(pdf_bytes: bytes, password: str | None = None) -> list[str]:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    if password:
        assert doc.authenticate(password)
    texts = [p.get_text().strip() for p in doc]
    doc.close()
    return texts


@pytest.fixture()
def workspace(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path / "ws")


@pytest.fixture()
def client(workspace: Workspace, tmp_path: Path):
    # static_dir を空ディレクトリにしてフロントエンドの有無に依存しないようにする
    app = create_app(workspace=workspace, token="", static_dir=tmp_path / "nofrontend")
    with TestClient(app) as c:
        yield c


def upload(client: TestClient, name: str, data: bytes, mime: str = "application/octet-stream") -> dict:
    res = client.post("/api/files", files={"file": (name, data, mime)})
    assert res.status_code == 200, res.text
    return res.json()


def download(client: TestClient, output: dict) -> bytes:
    res = client.get(f"/api/outputs/{output['id']}/download")
    assert res.status_code == 200, res.text
    return res.content
