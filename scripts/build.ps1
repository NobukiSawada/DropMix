# DropMix を Windows 用の単一 .exe にビルドするスクリプト
#
#   powershell -ExecutionPolicy Bypass -File scripts\build.ps1
#
# 前提: Python 3.10+ と Node.js 20+ がインストールされていること
# 出力: dist\DropMix.exe

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

function Invoke-Step($Title, [scriptblock]$Block) {
    Write-Host "==> $Title" -ForegroundColor Green
    & $Block
    if ($LASTEXITCODE -ne 0) { throw "$Title に失敗しました (exit $LASTEXITCODE)" }
}

# 1. Python 仮想環境
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Invoke-Step "仮想環境を作成" { python -m venv .venv }
}
$Py = Join-Path $Root ".venv\Scripts\python.exe"
Invoke-Step "Python ライブラリをインストール" { & $Py -m pip install --upgrade pip -q; & $Py -m pip install -r requirements.txt -r requirements-dev.txt -q }

# 2. フロントエンドのビルド
Push-Location frontend
try {
    Invoke-Step "npm ci" { npm ci }
    Invoke-Step "フロントエンドをビルド" { npm run build }
} finally {
    Pop-Location
}

# 3. テスト
Invoke-Step "テストを実行" { & $Py -m pytest -q }

# 4. アイコン生成 + PyInstaller
if (-not (Test-Path "assets\icon.ico")) {
    Invoke-Step "アイコンを生成" { & $Py scripts\make_icon.py }
}
Invoke-Step "PyInstaller でビルド" { & $Py -m PyInstaller dropmix.spec --noconfirm --clean }

Write-Host ""
Write-Host "完了: $(Join-Path $Root 'dist\DropMix.exe')" -ForegroundColor Green
