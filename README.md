# DropMix

**完全ローカルで動く、PDF・画像の結合／編集デスクトップアプリ**（Windows 向け）

ファイルを外部の Web サービスに送らず、自分の PC の中だけで PDF と画像を結合・並び替え・分割・圧縮・変換できます。白を基調に緑のアクセントを使った、シンプルな画面です。

---

## 主な機能

| 機能 | 内容 |
| --- | --- |
| **結合 (Merge)** | 複数の PDF と画像（JPG / PNG / WebP / BMP / GIF / TIFF）を、表示中の順番で 1 つの PDF にまとめます。画像は自動で PDF ページに変換されます。 |
| **プレビュー・並び替え** | すべてのページをサムネイルで一覧表示し、ドラッグ＆ドロップで並び替えます。ダブルクリックで拡大表示もできます。 |
| **分割・抽出 (Split / Extract)** | 1 ページずつ分割、範囲ごとに分割（例: `1-3, 5, 8-`）、指定ページだけを抽出、の 3 つから選べます。 |
| **PDF → 画像** | JPG / PNG で書き出します。解像度は 96〜400 dpi、JPG の画質も指定できます。 |
| **圧縮** | PyMuPDF の最適化（`garbage=4`, `deflate=True` など）を使います。「標準 / 高圧縮 / 最大圧縮」の 3 段階で、圧縮前後のサイズを表示します。 |
| **回転・削除** | 1 ページ単位でも、選択した複数ページでも、90° ずつ回転・削除できます。元に戻す／やり直す（Ctrl+Z / Ctrl+Y）に対応しています。 |
| **透かし** | 日本語にも対応したテキスト透かしを入れます。角度・サイズ・不透明度・色を指定できます。 |
| **ページ番号** | 6 か所の位置から選び、書式（`{n} / {total}` など）、開始番号、サイズ、色を指定して入れます。 |
| **パスワード** | AES-256 で暗号化し、印刷・コピー・編集を許可するかどうかも設定できます。パスワード付き PDF は、追加したときにパスワードを入力すればロックを解除できます。 |

### 操作のヒント

- ページをクリックで選択、Shift+クリックで範囲選択。選択がある場合は **選択したページだけ** が処理対象になります（なければ全ページ）。
- `Ctrl+A` 全選択 / `Delete` 選択ページを削除 / `Esc` 選択解除 / `Ctrl+O` ファイルを追加
- 画像は「長辺を A4 の長辺（842pt）に揃えたページ」に変換されます。元の解像度のまま埋め込むので、画質は落ちません。
- 処理結果は、デスクトップ版では Windows の保存ダイアログで保存します。複数ファイルになる場合は、選んだフォルダの中にサブフォルダを作って保存します。

---

## 技術スタック

- **フロントエンド**: React 19 + Vite + TypeScript + Tailwind CSS v4、shadcn/ui スタイルのコンポーネント（Radix UI）、react-dropzone、@dnd-kit、lucide-react、sonner（トースト）、zustand
- **バックエンド**: Python + FastAPI、PyMuPDF（`pymupdf`）、Pillow、python-multipart
- **デスクトップ化**: PyWebView（Windows では Edge WebView2）
- **パッケージング・CI/CD**: PyInstaller（単一 `.exe`）、GitHub Actions

### アーキテクチャ

```
┌──────────────── DropMix.exe ────────────────┐
│  PyWebView ウィンドウ (WebView2)              │
│     └ React UI ── fetch ──┐                  │
│                           ▼                  │
│  FastAPI (127.0.0.1:ランダムポート, 別スレッド) │
│     ├ PyMuPDF / Pillow で処理                  │
│     └ 一時ワークスペース (%TEMP%\dropmix-*)     │
└──────────────────────────────────────────────┘
```

- バックエンドは `127.0.0.1` の空いているポートでだけ待ち受けます。起動のたびにランダムなトークンを発行し、トークンのないリクエストは拒否します（同じ PC 上の他のプログラムや Web ページから API を使われないようにするため）。
- アップロードしたファイルは一時フォルダに置き、アプリの終了時に削除します。異常終了で残った一時フォルダは、次回起動時に削除します（24 時間以上更新のないもの）。
- 並び順・回転・削除はフロントエンドが「ページリスト」として持ち、各処理 API はそのページリストを受け取って処理します。

---

## フォルダ構成

```
DropMix/
├── main.py                  # デスクトップ起動スクリプト (PyWebView + uvicorn)
├── backend/                 # FastAPI バックエンド
│   ├── app.py               # アプリ生成、トークン認証、フロントエンド配信
│   ├── config.py            # 設定・パス解決 (PyInstaller 対応)
│   ├── schemas.py           # リクエストの型定義 (pydantic)
│   ├── workspace.py         # 一時ワークスペース (アップロード・出力の管理)
│   ├── api/
│   │   ├── files.py         # アップロード / サムネイル / ロック解除
│   │   ├── tools.py         # 結合・分割・画像化・圧縮・透かし・番号・保護
│   │   └── deps.py
│   └── services/
│       ├── pdf_ops.py       # PyMuPDF による PDF 処理
│       └── images.py        # 画像 → PDF 変換 (Pillow)
├── frontend/                # React + Vite + Tailwind
│   └── src/
│       ├── App.tsx
│       ├── store.ts         # 状態管理 (ページ順・選択・履歴)
│       ├── components/      # 画面部品 (グリッド・ツールパネル等)
│       │   ├── ui/          # shadcn/ui スタイルの基本コンポーネント
│       │   └── tools/       # 各ツールの設定画面
│       ├── hooks/
│       └── lib/             # API クライアント・型・ユーティリティ
├── tests/                   # pytest (API / PDF 処理 / デスクトップ連携)
├── scripts/
│   ├── build.ps1            # ローカルで exe を作るスクリプト
│   └── make_icon.py         # アイコン生成
├── assets/icon.ico
├── dropmix.spec             # PyInstaller 設定
├── requirements.txt         # 実行に必要なライブラリ
├── requirements-dev.txt     # テスト・ビルド用ライブラリ
└── .github/workflows/build.yml
```

---

## 使い方（配布版）

1. [Releases](../../releases) から `DropMix.exe` をダウンロードします。
2. ダブルクリックで起動します。Python のインストールは不要です。

> **動作要件**: Windows 10 / 11（64bit）と Microsoft Edge WebView2 ランタイム。WebView2 は Windows 11 と最近の Windows 10 には標準で入っています。入っていない場合は [Microsoft の配布ページ](https://developer.microsoft.com/microsoft-edge/webview2/) からインストールしてください。
>
> **注意**: exe はコード署名していないため、初回起動時に Windows SmartScreen の警告が出ることがあります（「詳細情報」→「実行」で起動できます）。Smart App Control（スマート アプリ コントロール）が有効な PC では、署名のない exe の実行がブロックされます。その場合は、下の「開発環境で実行する」の方法で起動してください。

---

## 開発

### 必要なもの

- Python 3.10 以上（3.12 / 3.13 で動作確認）
- Node.js 20 以上（22 / 24 で動作確認）

### セットアップ

```powershell
# Python
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt

# フロントエンド
cd frontend
npm ci
cd ..
```

### 開発環境で実行する

**A. デスクトップウィンドウで実行**（ビルド済みのフロントエンドを使う）

```powershell
cd frontend; npm run build; cd ..
python main.py            # --debug で開発者ツールを有効にする
```

**B. ホットリロードで開発**（ターミナルを 2 つ使う）

```powershell
# ターミナル 1: Vite 開発サーバー (http://localhost:5173)
cd frontend; npm run dev

# ターミナル 2: バックエンド (ポート 8000) と PyWebView ウィンドウ
python main.py --dev
```

ブラウザだけで確認する場合は、ターミナル 2 で `uvicorn backend.app:create_app --factory --port 8000 --reload` を実行し、http://localhost:5173 を開きます。ブラウザでは、結果は保存ダイアログではなく通常のダウンロード（複数ファイルは ZIP）になります。

### テスト

```powershell
python -m pytest -q             # バックエンド (API / PDF 処理 / デスクトップ連携)
cd frontend; npm run lint       # TypeScript の型チェック
```

### exe のビルド（ローカル）

```powershell
powershell -ExecutionPolicy Bypass -File scripts\build.ps1
```

依存関係のインストール → フロントエンドのビルド → テスト → PyInstaller の順に実行し、`dist\DropMix.exe` を作ります。手動で行う場合は次のとおりです。

```powershell
cd frontend; npm ci; npm run build; cd ..
pyinstaller dropmix.spec --noconfirm --clean
dist\DropMix.exe --smoke-test   # ウィンドウを開かずに起動確認 (終了コード 0 なら OK)
```

---

## CI/CD（GitHub Actions）

`.github/workflows/build.yml` が Windows ランナー上で次の処理を行います。

| トリガー | 処理 |
| --- | --- |
| `main` への push / Pull Request | フロントエンドのビルド → pytest → PyInstaller で exe をビルド → exe の起動確認（`--smoke-test`）→ Artifacts に `DropMix.exe` をアップロード |
| `v*` タグの push（例: `v1.0.0`） | 上記に加えて、**GitHub Releases に `DropMix.exe` を自動でアップロード**（リリースノートも自動生成） |

リリースの手順:

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## API（参考）

起動中は `/api/docs` で Swagger UI を見られます（デスクトップ版ではトークンが必要です）。

| メソッド | パス | 説明 |
| --- | --- | --- |
| POST | `/api/files` | ファイルを追加（multipart, `file`） |
| POST | `/api/files/{id}/unlock` | パスワード付き PDF のロックを解除 |
| GET | `/api/files/{id}/pages/{n}/thumbnail?w=` | サムネイル（JPEG） |
| DELETE | `/api/files/{id}` / `/api/files` | ファイルを閉じる / すべて閉じる |
| POST | `/api/merge` `/api/split` `/api/to-images` `/api/compress` `/api/watermark` `/api/page-numbers` `/api/protect` | 各処理。body は `{"pages": [{"file_id", "index", "rotation"}], ...オプション}` |
| GET | `/api/outputs/{id}/download` | 処理結果（複数ファイルの場合は ZIP） |

---

## ライセンスについて

PyMuPDF は **AGPL-3.0**（または Artifex の商用ライセンス）で提供されています。DropMix を配布する場合は AGPL の条件（ソースコードの公開など）に従うか、商用ライセンスを取得してください。
