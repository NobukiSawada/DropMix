# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for DropMix (single-file, windowed .exe)
#
#   cd frontend && npm ci && npm run build && cd ..
#   pyinstaller dropmix.spec --noconfirm --clean
#
# 出力: dist/DropMix.exe

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH)
FRONTEND_DIST = ROOT / "frontend" / "dist"
ICON = ROOT / "assets" / "icon.ico"

if not (FRONTEND_DIST / "index.html").is_file():
    raise SystemExit("frontend/dist がありません。先に `npm run build` を実行してください。")

hiddenimports = [
    *collect_submodules("uvicorn"),
    *collect_submodules("backend"),
    "multipart",
    "python_multipart",
]

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[(str(FRONTEND_DIST), "frontend_dist")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "matplotlib",
        "numpy",
        "pandas",
        "pytest",
        "playwright",
        "IPython",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DropMix",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ICON) if ICON.is_file() else None,
    version=None,
)
