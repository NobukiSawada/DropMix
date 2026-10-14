"""DropMix desktop launcher.

Starts the FastAPI backend on a random localhost port in a background thread and
shows the React UI in a native window via PyWebView.

    python main.py            # 通常起動 (frontend/dist を表示)
    python main.py --dev      # 開発モード (Vite dev server http://localhost:5173 を表示)
    python main.py --debug    # 開発者ツールを有効化
"""

from __future__ import annotations

import argparse
import logging
import os
import secrets
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

# PyInstaller の --windowed ビルドでは stdout/stderr が None になり、
# uvicorn 等のログ出力で落ちるため、先に差し替えておく
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")  # noqa: SIM115

import uvicorn  # noqa: E402
import webview  # noqa: E402

from backend import __version__  # noqa: E402
from backend.app import create_app  # noqa: E402
from backend.config import frontend_dist_dir  # noqa: E402
from backend.workspace import NotFoundError, Workspace, purge_stale_workspaces  # noqa: E402

log = logging.getLogger("dropmix")

APP_NAME = "DropMix"
DEV_SERVER_URL = "http://localhost:5173"
DEV_API_PORT = 8000

_FILE_TYPE_LABELS = {
    ".pdf": "PDF ファイル",
    ".jpg": "JPEG 画像",
    ".png": "PNG 画像",
    ".zip": "ZIP ファイル",
}


def setup_logging(debug: bool) -> None:
    handlers: list[logging.Handler] = []
    if getattr(sys, "frozen", False):
        log_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_NAME / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_dir / "dropmix.log", encoding="utf-8"))
    else:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


class DesktopApi:
    """Functions exposed to JavaScript as ``window.pywebview.api``.

    Attributes starting with ``_`` are not exposed to JavaScript.
    """

    def __init__(self, workspace: Workspace) -> None:
        self._workspace = workspace
        self._window: webview.Window | None = None
        self._last_dir = str(Path.home() / "Downloads") if (Path.home() / "Downloads").is_dir() else ""

    def save_output(self, output_id: str) -> dict:
        """Show a native save dialog and copy the generated output there."""
        window = self._window
        if window is None:
            return {"saved": False, "error": "ウィンドウが初期化されていません"}
        try:
            output = self._workspace.get_output(output_id)
        except NotFoundError:
            return {"saved": False, "error": "出力ファイルが見つかりません。もう一度実行してください"}

        try:
            if len(output.files) == 1:
                name = output.files[0]
                ext = Path(name).suffix.lower()
                label = _FILE_TYPE_LABELS.get(ext, "ファイル")
                result = window.create_file_dialog(
                    webview.FileDialog.SAVE,
                    directory=self._last_dir,
                    save_filename=name,
                    file_types=(f"{label} (*{ext})", "すべてのファイル (*.*)"),
                )
                if not result:
                    return {"saved": False}
                target = Path(result if isinstance(result, str) else result[0])
                if not target.suffix:
                    target = target.with_suffix(ext)
                self._workspace.save_output_to(output_id, target)
                self._last_dir = str(target.parent)
                return {"saved": True, "path": str(target)}

            # 複数ファイル: 保存先フォルダを選ばせ、その中にサブフォルダを作って書き出す
            result = window.create_file_dialog(webview.FileDialog.FOLDER, directory=self._last_dir)
            if not result:
                return {"saved": False}
            parent = Path(result if isinstance(result, str) else result[0])
            folder = parent / Path(output.download_name).stem
            n = 2
            while folder.exists():
                folder = parent / f"{Path(output.download_name).stem}({n})"
                n += 1
            self._workspace.save_output_to(output_id, folder)
            self._last_dir = str(parent)
            return {"saved": True, "path": str(folder)}
        except OSError as exc:
            log.exception("save failed")
            return {"saved": False, "error": f"保存に失敗しました: {exc}"}

    def open_path(self, path: str) -> bool:
        """Open a saved folder (or reveal a saved file) in Explorer."""
        p = Path(path)
        try:
            if sys.platform == "win32":
                if p.is_file():
                    subprocess.Popen(["explorer", "/select,", str(p)])  # noqa: S603, S607
                elif p.exists():
                    os.startfile(p)  # type: ignore[attr-defined]  # noqa: S606
                else:
                    return False
            elif sys.platform == "darwin":
                subprocess.Popen(["open", "-R", str(p)] if p.is_file() else ["open", str(p)])  # noqa: S603, S607
            else:
                subprocess.Popen(["xdg-open", str(p if p.is_dir() else p.parent)])  # noqa: S603, S607
            return True
        except OSError:
            log.exception("open_path failed")
            return False


class BackendServer:
    """Runs uvicorn in a daemon thread."""

    def __init__(self, app, port: int | None) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind(("127.0.0.1", port or 0))
        self.port = self.sock.getsockname()[1]
        config = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_config=None, access_log=False)
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self._run, name="dropmix-backend", daemon=True)

    def _run(self) -> None:
        self.server.run(sockets=[self.sock])

    def start(self, timeout: float = 20) -> None:
        self.thread.start()
        deadline = time.monotonic() + timeout
        while not self.server.started:
            if not self.thread.is_alive():
                raise RuntimeError("バックエンドの起動に失敗しました")
            if time.monotonic() > deadline:
                raise RuntimeError("バックエンドの起動がタイムアウトしました")
            time.sleep(0.02)

    def stop(self) -> None:
        self.server.should_exit = True
        self.thread.join(timeout=5)


def smoke_test(port: int, token: str) -> int:
    """Verify that the bundled UI and the API respond (used by CI on the built .exe)."""
    import urllib.error
    import urllib.request

    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(f"{base}/", timeout=10) as res:  # noqa: S310
            if b'id="root"' not in res.read():
                raise RuntimeError("index.html の内容が不正です")
        req = urllib.request.Request(f"{base}/api/health", headers={"X-DropMix-Token": token})
        with urllib.request.urlopen(req, timeout=10) as res:  # noqa: S310
            if res.status != 200:
                raise RuntimeError(f"health: HTTP {res.status}")
        try:
            urllib.request.urlopen(f"{base}/api/health", timeout=10)  # noqa: S310
            raise RuntimeError("トークンなしで API にアクセスできてしまいます")
        except urllib.error.HTTPError as exc:
            if exc.code != 403:
                raise
        import pymupdf  # noqa: F401  # バンドルされたネイティブライブラリの読み込み確認
    except Exception:
        log.exception("smoke test failed")
        print("SMOKE TEST FAILED", file=sys.stderr)
        return 1
    log.info("smoke test passed")
    print("SMOKE TEST OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DropMix - ローカルPDF・画像処理アプリ")
    parser.add_argument("--dev", action="store_true", help="Vite 開発サーバーの画面を表示する")
    parser.add_argument("--debug", action="store_true", help="開発者ツールを有効にする")
    parser.add_argument("--port", type=int, default=None, help="バックエンドのポート (既定: 空きポート)")
    parser.add_argument(
        "--smoke-test", action="store_true", help="ウィンドウを開かずに起動確認だけ行って終了する (CI 用)"
    )
    args = parser.parse_args(argv)

    setup_logging(args.debug)
    log.info("DropMix %s starting", __version__)

    purge_stale_workspaces()
    workspace = Workspace()
    # 開発モードでは Vite のプロキシ (固定ポート) から呼ぶためトークンを使わない
    token = "" if args.dev else secrets.token_urlsafe(32)
    app = create_app(workspace=workspace, token=token)

    if not args.dev and not (frontend_dist_dir() / "index.html").is_file():
        log.error("frontend build not found: %s", frontend_dist_dir())
        print("frontend/dist が見つかりません。先に `cd frontend && npm run build` を実行してください。", file=sys.stderr)
        workspace.cleanup()
        return 1

    server = BackendServer(app, DEV_API_PORT if args.dev else args.port)
    try:
        server.start()
        url = DEV_SERVER_URL if args.dev else f"http://127.0.0.1:{server.port}/?token={token}"
        log.info("backend listening on 127.0.0.1:%s", server.port)

        if args.smoke_test:
            return smoke_test(server.port, token)

        api = DesktopApi(workspace)
        window = webview.create_window(
            APP_NAME,
            url=url,
            js_api=api,
            width=1320,
            height=860,
            min_size=(1040, 660),
            background_color="#FFFFFF",
            text_select=False,
        )
        api._window = window
        webview.settings["OPEN_DEVTOOLS_IN_DEBUG"] = args.debug
        webview.start(debug=args.debug, private_mode=True)
    finally:
        server.stop()
        workspace.cleanup()
        log.info("DropMix exited")
    return 0


if __name__ == "__main__":
    sys.exit(main())
