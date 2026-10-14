"""Tests for the PyWebView bridge in main.py (native dialogs are faked)."""

from __future__ import annotations

import os
import time

import pytest

import main
from backend.workspace import Workspace, purge_stale_workspaces


class FakeWindow:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def create_file_dialog(self, dialog_type, **kwargs):
        self.calls.append((dialog_type, kwargs))
        return self.result


@pytest.fixture()
def ws(tmp_path):
    return Workspace(tmp_path / "ws")


def make_api(ws, result):
    api = main.DesktopApi(ws)
    api._window = FakeWindow(result)
    return api


def test_save_single_file(ws, tmp_path):
    out = ws.create_output([("a.pdf", b"%PDF-1")])
    target = tmp_path / "dest" / "saved"
    api = make_api(ws, str(target))
    res = api.save_output(out.id)
    # 拡張子がなければ補われる
    assert res == {"saved": True, "path": str(target.with_suffix(".pdf"))}
    assert target.with_suffix(".pdf").read_bytes() == b"%PDF-1"
    dialog_type, kwargs = api._window.calls[0]
    assert dialog_type == main.webview.FileDialog.SAVE
    assert kwargs["save_filename"] == "a.pdf"


def test_save_multiple_files_into_subfolder(ws, tmp_path):
    out = ws.create_output([("doc_p1.pdf", b"1"), ("doc_p2.pdf", b"2")])
    api = make_api(ws, (str(tmp_path),))
    res = api.save_output(out.id)
    assert res["saved"]
    folder = tmp_path / "doc"
    assert res["path"] == str(folder)
    assert sorted(p.name for p in folder.iterdir()) == ["doc_p1.pdf", "doc_p2.pdf"]
    # 2回目は別フォルダに保存される
    res2 = api.save_output(out.id)
    assert res2["path"] == str(tmp_path / "doc(2)")


def test_save_cancelled(ws):
    out = ws.create_output([("a.pdf", b"x")])
    assert make_api(ws, None).save_output(out.id) == {"saved": False}


def test_save_unknown_output(ws):
    res = make_api(ws, None).save_output("nope")
    assert res["saved"] is False and "error" in res


def test_save_without_window(ws):
    out = ws.create_output([("a.pdf", b"x")])
    res = main.DesktopApi(ws).save_output(out.id)
    assert res["saved"] is False and "error" in res


def test_open_path_missing(ws, tmp_path):
    assert main.DesktopApi(ws).open_path(str(tmp_path / "missing")) is False


def test_purge_stale_workspaces():
    old = Workspace()
    fresh = Workspace()
    try:
        past = time.time() - 3 * 24 * 3600
        for p in (old.root, old.root / "files", old.root / "outputs"):
            os.utime(p, (past, past))
        purge_stale_workspaces(max_age_hours=24)
        assert not old.root.exists()
        assert fresh.root.exists()
    finally:
        old.cleanup()
        fresh.cleanup()
