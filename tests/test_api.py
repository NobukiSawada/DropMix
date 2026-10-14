from __future__ import annotations

import io
import zipfile

import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app import create_app

from .conftest import download, make_image, make_pdf, page_texts, upload


def pages_of(*files: dict) -> list[dict]:
    return [{"file_id": f["id"], "index": i} for f in files for i in range(f["page_count"])]


# --- upload ------------------------------------------------------------------


def test_upload_pdf(client):
    info = upload(client, "doc.pdf", make_pdf(["A", "B", "C"]))
    assert info["kind"] == "pdf"
    assert info["page_count"] == 3
    assert info["locked"] is False
    assert info["pages"][0]["width"] == pytest.approx(595)


@pytest.mark.parametrize("fmt,name", [("PNG", "a.png"), ("JPEG", "a.jpg"), ("WEBP", "a.webp"), ("BMP", "a.bmp")])
def test_upload_image_is_converted_to_single_page(client, fmt, name):
    info = upload(client, name, make_image(fmt, size=(400, 200)))
    assert info["kind"] == "image"
    assert info["page_count"] == 1
    page = info["pages"][0]
    # 長辺が A4 長辺に揃い、縦横比が維持される
    assert page["width"] == pytest.approx(842, abs=0.5)
    assert page["height"] == pytest.approx(421, abs=0.5)


def test_upload_rgba_and_palette_png(client):
    upload(client, "rgba.png", make_image("PNG", mode="RGBA", color=(0, 0, 0, 0)))
    upload(client, "p.png", make_image("PNG", mode="P", color=3))


def test_upload_exif_rotated_jpeg(client):
    img = Image.new("RGB", (400, 200), (10, 20, 30))
    exif = img.getexif()
    exif[0x0112] = 6  # 90° 回転して表示すべき画像
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=exif)
    info = upload(client, "rot.jpg", buf.getvalue())
    page = info["pages"][0]
    assert page["height"] > page["width"]


def test_upload_rejects_unknown_type(client):
    res = client.post("/api/files", files={"file": ("a.txt", b"hello", "text/plain")})
    assert res.status_code == 415


def test_upload_rejects_broken_pdf(client, workspace):
    res = client.post("/api/files", files={"file": ("bad.pdf", b"not a pdf at all", "application/pdf")})
    assert res.status_code == 400
    assert workspace.list_files() == []


def test_upload_rejects_broken_image(client):
    res = client.post("/api/files", files={"file": ("bad.png", b"\x89PNG broken", "image/png")})
    assert res.status_code == 400


def test_list_delete_and_clear(client):
    a = upload(client, "a.pdf", make_pdf(["A"]))
    upload(client, "b.pdf", make_pdf(["B"]))
    assert len(client.get("/api/files").json()) == 2
    assert client.delete(f"/api/files/{a['id']}").status_code == 200
    assert client.delete(f"/api/files/{a['id']}").status_code == 404
    assert len(client.get("/api/files").json()) == 1
    client.delete("/api/files")
    assert client.get("/api/files").json() == []


def test_thumbnail(client):
    info = upload(client, "doc.pdf", make_pdf(["A", "B"]))
    res = client.get(f"/api/files/{info['id']}/pages/1/thumbnail?w=200")
    assert res.status_code == 200
    assert res.headers["content-type"] == "image/jpeg"
    img = Image.open(io.BytesIO(res.content))
    assert img.width == 240  # 80px 単位に丸められる
    assert client.get(f"/api/files/{info['id']}/pages/5/thumbnail").status_code == 404
    assert client.get("/api/files/nope/pages/0/thumbnail").status_code == 404


# --- password protected input --------------------------------------------------


def test_locked_pdf_requires_unlock(client):
    info = upload(client, "secret.pdf", make_pdf(["S1", "S2"], password="pw"))
    assert info["locked"] is True
    assert info["page_count"] == 0

    res = client.post("/api/merge", json={"pages": [{"file_id": info["id"], "index": 0}]})
    assert res.status_code == 400

    res = client.post(f"/api/files/{info['id']}/unlock", json={"password": "wrong"})
    assert res.status_code == 400
    assert "パスワード" in res.json()["detail"]

    res = client.post(f"/api/files/{info['id']}/unlock", json={"password": "pw"})
    assert res.status_code == 200
    unlocked = res.json()
    assert unlocked["locked"] is False
    assert unlocked["page_count"] == 2

    out = client.post("/api/merge", json={"pages": pages_of(unlocked)}).json()
    # 解除後の出力はパスワードなしで開ける
    assert page_texts(download(client, out)) == ["S1", "S2"]


# --- merge ---------------------------------------------------------------------


def test_merge_mixed_order_and_rotation(client):
    a = upload(client, "a.pdf", make_pdf(["A1", "A2", "A3"]))
    img = upload(client, "pic.png", make_image())
    b = upload(client, "b.pdf", make_pdf(["B1"]))
    pages = [
        {"file_id": b["id"], "index": 0},
        {"file_id": a["id"], "index": 2, "rotation": 90},
        {"file_id": img["id"], "index": 0},
        {"file_id": a["id"], "index": 0, "rotation": 270},
        {"file_id": a["id"], "index": 1},
    ]
    out = client.post("/api/merge", json={"pages": pages}).json()
    assert out["files"] == ["b_merged.pdf"]
    data = download(client, out)
    assert page_texts(data) == ["B1", "A3", "", "A1", "A2"]
    doc = pymupdf.open(stream=data, filetype="pdf")
    assert [p.rotation for p in doc] == [0, 90, 0, 270, 0]
    assert doc[2].get_images()  # 画像ページには画像が埋め込まれている
    doc.close()


def test_merge_custom_output_name(client):
    a = upload(client, "a.pdf", make_pdf(["A"]))
    out = client.post("/api/merge", json={"pages": pages_of(a), "output_name": "まとめ.pdf"}).json()
    assert out["files"] == ["まとめ.pdf"]
    res = client.get(f"/api/outputs/{out['id']}/download")
    assert "filename*=utf-8''" in res.headers["content-disposition"].lower()


def test_merge_validation(client):
    assert client.post("/api/merge", json={"pages": []}).status_code == 422
    assert client.post("/api/merge", json={"pages": [{"file_id": "x", "index": 0}]}).status_code == 404
    a = upload(client, "a.pdf", make_pdf(["A"]))
    assert client.post("/api/merge", json={"pages": [{"file_id": a["id"], "index": 3}]}).status_code == 400
    assert client.post("/api/merge", json={"pages": [{"file_id": a["id"], "index": 0, "rotation": 45}]}).status_code == 422


# --- split ---------------------------------------------------------------------


def _zip_entries(data: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        return {n: zf.read(n) for n in zf.namelist()}


def test_split_each(client):
    a = upload(client, "doc.pdf", make_pdf([f"P{i}" for i in range(1, 12)]))
    out = client.post("/api/split", json={"pages": pages_of(a), "mode": "each"}).json()
    assert len(out["files"]) == 11
    assert out["files"][0] == "doc_p01.pdf"
    assert out["download_name"] == "doc.zip"
    entries = _zip_entries(download(client, out))
    assert page_texts(entries["doc_p11.pdf"]) == ["P11"]


def test_split_ranges_and_extract(client):
    a = upload(client, "doc.pdf", make_pdf([f"P{i}" for i in range(1, 7)]))
    out = client.post("/api/split", json={"pages": pages_of(a), "mode": "ranges", "ranges": "1-2, 4, 5-"}).json()
    assert out["files"] == ["doc_p1-2.pdf", "doc_p4.pdf", "doc_p5-6.pdf"]
    entries = _zip_entries(download(client, out))
    assert page_texts(entries["doc_p5-6.pdf"]) == ["P5", "P6"]

    out = client.post("/api/split", json={"pages": pages_of(a), "mode": "extract", "ranges": "6,1-2"}).json()
    assert out["files"] == ["doc_extract.pdf"]
    assert page_texts(download(client, out)) == ["P6", "P1", "P2"]


@pytest.mark.parametrize("spec", ["", "0", "3-1", "1-99", "abc", "1--2"])
def test_split_invalid_ranges(client, spec):
    a = upload(client, "doc.pdf", make_pdf(["A", "B", "C"]))
    res = client.post("/api/split", json={"pages": pages_of(a), "mode": "ranges", "ranges": spec})
    assert res.status_code == 400


# --- images ----------------------------------------------------------------------


def test_to_images_jpg_and_png(client):
    a = upload(client, "doc.pdf", make_pdf(["A", "B"], width=200, height=100))
    out = client.post("/api/to-images", json={"pages": pages_of(a), "format": "png", "dpi": 144}).json()
    assert out["files"] == ["doc_p01.png", "doc_p02.png"]
    entries = _zip_entries(download(client, out))
    img = Image.open(io.BytesIO(entries["doc_p01.png"]))
    assert img.size == (400, 200)

    out = client.post(
        "/api/to-images", json={"pages": [{"file_id": a["id"], "index": 1, "rotation": 90}], "format": "jpg", "dpi": 72}
    ).json()
    assert out["files"] == ["doc_p01.jpg"]
    img = Image.open(io.BytesIO(download(client, out)))
    assert img.format == "JPEG"
    assert img.size == (100, 200)  # 回転が反映される


# --- compress ----------------------------------------------------------------------


def _photo_pdf() -> bytes:
    # ノイズ画像を高解像度で埋め込んだ PDF (圧縮の効果が出やすい)
    import os

    img = Image.frombytes("RGB", (1600, 1600), os.urandom(1600 * 1600 * 3))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=300)
    page.insert_image(page.rect, stream=buf.getvalue())
    data = doc.tobytes()
    doc.close()
    return data


@pytest.mark.parametrize("level", ["standard", "strong", "max"])
def test_compress(client, level):
    a = upload(client, "photo.pdf", _photo_pdf())
    out = client.post("/api/compress", json={"pages": pages_of(a), "level": level}).json()
    assert out["files"] == ["photo_compressed.pdf"]
    assert out["size_after"] == len(download(client, out))
    if level != "standard":
        assert out["size_after"] < out["size_before"] * 0.5
    doc = pymupdf.open(stream=download(client, out), filetype="pdf")
    assert doc.page_count == 1
    doc.close()


# --- watermark / page numbers --------------------------------------------------------


@pytest.mark.parametrize("text", ["CONFIDENTIAL", "社外秘"])
def test_watermark(client, text):
    a = upload(client, "doc.pdf", make_pdf(["A", "B"]))
    pages = [{"file_id": a["id"], "index": 0}, {"file_id": a["id"], "index": 1, "rotation": 90}]
    out = client.post("/api/watermark", json={"pages": pages, "text": text}).json()
    texts = page_texts(download(client, out))
    assert all(text in t for t in texts)


@pytest.mark.parametrize("rotation", [0, 90, 180, 270])
def test_watermark_is_centered_and_diagonal_on_rotated_pages(client, rotation):
    a = upload(client, "doc.pdf", make_pdf([""]))
    pages = [{"file_id": a["id"], "index": 0, "rotation": rotation}]
    out = client.post("/api/watermark", json={"pages": pages, "text": "DRAFT", "angle": 45}).json()
    doc = pymupdf.open(stream=download(client, out), filetype="pdf")
    page = doc[0]
    lines = [l for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])]
    assert len(lines) == 1
    # get_text は未回転座標系で返すため、表示座標系に変換して確認する
    direction = pymupdf.Point(lines[0]["dir"]) * pymupdf.Matrix(rotation)
    assert direction.x == pytest.approx(0.7071, abs=0.01)
    assert direction.y == pytest.approx(-0.7071, abs=0.01)  # 右上がり
    bbox = pymupdf.Rect(lines[0]["bbox"]) * page.rotation_matrix
    assert abs((bbox.x0 + bbox.x1) / 2 - page.rect.width / 2) < 15
    assert abs((bbox.y0 + bbox.y1) / 2 - page.rect.height / 2) < 15
    doc.close()


def test_japanese_watermark_font_is_subset(client):
    a = upload(client, "doc.pdf", make_pdf(["A"]))
    out = client.post("/api/watermark", json={"pages": pages_of(a), "text": "社外秘"}).json()
    # 内蔵 CJK フォント (約3.5MB) を丸ごと埋め込まない
    assert out["total_size"] < 200_000


def test_page_numbers(client):
    a = upload(client, "doc.pdf", make_pdf(["A", "B", "C"]))
    out = client.post(
        "/api/page-numbers", json={"pages": pages_of(a), "position": "bottom-right", "format": "{n} / {total}"}
    ).json()
    texts = page_texts(download(client, out))
    assert "1 / 3" in texts[0] and "3 / 3" in texts[2]

    out = client.post(
        "/api/page-numbers", json={"pages": pages_of(a), "format": "- {n} ページ -", "start": 5, "position": "top-left"}
    ).json()
    texts = page_texts(download(client, out))
    assert "- 7 ページ -" in texts[2]

    res = client.post("/api/page-numbers", json={"pages": pages_of(a), "format": "no number"})
    assert res.status_code == 400


def test_page_numbers_position_on_rotated_page(client):
    a = upload(client, "doc.pdf", make_pdf(["A"]))
    out = client.post(
        "/api/page-numbers",
        json={"pages": [{"file_id": a["id"], "index": 0, "rotation": 90}], "position": "bottom-center", "format": "{n}"},
    ).json()
    doc = pymupdf.open(stream=download(client, out), filetype="pdf")
    page = doc[0]
    lines = [
        l
        for b in page.get_text("dict")["blocks"]
        for l in b.get("lines", [])
        if "".join(s["text"] for s in l["spans"]).strip() == "1"
    ]
    assert len(lines) == 1
    # 表示座標で見たときにページ下部・水平中央にあり、文字が水平であること
    r = pymupdf.Rect(lines[0]["bbox"]) * page.rotation_matrix
    assert r.y0 > page.rect.height * 0.8
    assert abs((r.x0 + r.x1) / 2 - page.rect.width / 2) < 20
    direction = pymupdf.Point(lines[0]["dir"]) * pymupdf.Matrix(90)
    assert direction.x == pytest.approx(1, abs=0.01)
    doc.close()


# --- protect -------------------------------------------------------------------------


def test_protect(client):
    a = upload(client, "doc.pdf", make_pdf(["A", "B"]))
    out = client.post("/api/protect", json={"pages": pages_of(a), "user_password": "secret"}).json()
    data = download(client, out)
    doc = pymupdf.open(stream=data, filetype="pdf")
    assert doc.needs_pass
    assert not doc.authenticate("wrong")
    doc.close()
    assert page_texts(data, password="secret") == ["A", "B"]


# --- outputs / security -----------------------------------------------------------------


def test_unknown_output(client):
    assert client.get("/api/outputs/unknown/download").status_code == 404


def test_token_required(workspace, tmp_path):
    app = create_app(workspace=workspace, token="s3cret", static_dir=tmp_path / "none")
    with TestClient(app) as c:
        assert c.get("/api/health").status_code == 403
        assert c.get("/api/health", headers={"X-DropMix-Token": "bad"}).status_code == 403
        assert c.get("/api/health", headers={"X-DropMix-Token": "s3cret"}).status_code == 200
        assert c.get("/api/health?token=s3cret").status_code == 200


def test_spa_serving(workspace, tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html>DropMix</html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    (dist / "favicon.svg").write_text("<svg/>", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("nope", encoding="utf-8")
    app = create_app(workspace=workspace, token="", static_dir=dist)
    with TestClient(app) as c:
        assert "DropMix" in c.get("/").text
        assert "DropMix" in c.get("/some/route").text
        assert c.get("/assets/app.js").text == "console.log(1)"
        assert c.get("/favicon.svg").text == "<svg/>"
        assert "nope" not in c.get("/../secret.txt").text
        assert c.get("/api/unknown").status_code == 404


def test_compress_reports_original_file_size(client):
    data = _photo_pdf()
    a = upload(client, "photo.pdf", data)
    out = client.post("/api/compress", json={"pages": pages_of(a), "level": "strong"}).json()
    assert out["size_before"] == len(data)


def test_concurrent_requests_are_safe(client):
    """MuPDF はスレッドセーフではないため、並列リクエストでも壊れないことを確認する."""
    from concurrent.futures import ThreadPoolExecutor

    a = upload(client, "doc.pdf", make_pdf([f"P{i}" for i in range(1, 21)]))

    def thumb(i: int) -> int:
        return client.get(f"/api/files/{a['id']}/pages/{i % 20}/thumbnail?w={160 + (i % 3) * 80}").status_code

    def merge(_: int) -> int:
        return client.post("/api/merge", json={"pages": pages_of(a)}).status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        results = list(pool.map(thumb, range(60))) + list(pool.map(merge, range(12)))
    assert set(results) == {200}


def test_parse_ranges_accepts_spaces_and_japanese_tilde():
    from backend.services.pdf_ops import parse_ranges

    assert parse_ranges("1 - 3, 5", 6) == [[0, 1, 2], [4]]
    assert parse_ranges("2〜3、 6", 6) == [[1, 2], [5]]
    assert parse_ranges("-2", 6) == [[0, 1]]
