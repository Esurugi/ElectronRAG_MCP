以下のように README を修正してください。仮想環境を使わず、依存パッケージをプロジェクト内の `py/` ディレクトリにインストールし、そのまま MCP サーバー／クライアントを実行できるようになります。

---

## ElectronRAG_MCP README

### 概要
このリポジトリは、Electron API ドキュメントをローカルで RAG（Retrieval‑Augmented Generation）システムとして検索できる MCP サーバー／クライアント実装です。  
依存ライブラリはすべてプロジェクト配下の `py/` フォルダにインストールし、仮想環境なしで動作します。

---

## ディレクトリ構成例

```
ElectronRAG_MCP/
├── py/                     ← 依存ライブラリをインストールするフォルダ
├── server.py               ← MCP サーバー用スクリプト
├── test_client.py          ← 動作確認用クライアントスクリプト
├── requirements.txt        ← 必要パッケージ一覧
├── electron-api.json       ← Electron ドキュメント JSON
└── README.md
```

---

## セットアップ手順

### 1. 必要ツールのインストール
- Python 3.11 以上
- Node.js 18 以上
- pip（Python に同梱）

### 2. 依存パッケージを `py/` にインストール

```bash
# プロジェクトルートで実行
pip install --upgrade pip setuptools
pip install -r requirements.txt --target py
```

- `requirements.txt` の中身例：
  ```
  mcp[cli]>=1.6.0
  sentence-transformers>=2.2.0
  faiss-cpu>=1.7.3
  numpy>=1.24.0
  ```
- すべてのパッケージが `py/` 配下にダウンロードされます。

### 3. `py/` を検索パスに追加

#### macOS/Linux の場合

```bash
export PYTHONPATH="$(pwd)/py:$PYTHONPATH"
```

#### Windows PowerShell の場合

```powershell
$env:PYTHONPATH = "$PWD\py;" + $env:PYTHONPATH
```

- これにより、`import mcp` などが `py/` 配下のライブラリを参照するようになります。

---

## Electron ドキュメント JSON の準備

公式ドキュメントを JSON 化して `electron-api.json` を用意します（すでにある場合はスキップ）。

```bash
# 必要に応じて一度だけ実行
npm install -g @electron/docs-parser
electron-docs-parser --dir ./electron-repo/docs/api --moduleVersion 30.0.0
```

---

## サーバーの起動方法

```bash
# JSON のパスやオプションを必要に応じて調整
python server.py \
  --json_path electron-api.json \
  --alpha 0.7           # ベクトル検索の重み (0.0～1.0)
  # --no_reranker       # 再ランキングを無効化したい場合
  # --no_rrf            # RRF 融合を無効化したい場合
```

- コマンド実行後、次のように表示されれば成功です：  
  ```
  Loaded Electron API JSON with XXX modules
  Generated YYY chunks in Z.ZZ seconds
  Initialized search engine in W.WW seconds
  Starting MCP server for Electron API documentation search...
  ```

---

## Claude Desktop などからの接続設定

1. **設定ファイルを開く**  
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`  
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`  

2. **mcpServers セクションに追記**

   ```jsonc
   {
     "mcpServers": {
       "ElectronRAG": {
         "command": "python",
         "args": [
           "C:/path/to/ElectronRAG_MCP/server.py",
           "--json_path", "C:/path/to/ElectronRAG_MCP/electron-api.json",
           "--alpha", "0.7"
         ],
         "env": {
           "PYTHONPATH": "C:/path/to/ElectronRAG_MCP/py"
         }
       }
     }
   }
   ```

3. **Claude Desktop を再起動**  
   「ElectronRAG」というサーバーが選択可能になります。

---

## クライアント動作確認

CLI からも動作を確認できます。

```bash
python test_client.py \
  --mode english \
  --keywords window create \
  --top_k 5 \
  --server_script server.py
```

**出力例**  
```
MCPサーバーに接続しています: server.py
利用可能なツール: ['search_docs']
検索キーワード: ['window', 'create']
5件の結果が見つかりました:
1. BrowserWindow (スコア: 0.8765)
   種類: class
   説明: Electron のウィンドウを作成するためのクラスです...
```

---

## トラブルシューティング

- **依存パッケージが見つからない**  
  - `PYTHONPATH` に必ず `py/` フォルダを含めているか確認してください。  
  - 実行中の `python` が同じバージョンかも要チェックです。

- **空の結果しか返らない**  
  - サーバー起動時のログで「Loaded」「Generated」「Initialized」の各メッセージが出力されているか確認。  
  - `electron-api.json` が最新か、正しいバージョン（`--moduleVersion`）で生成されているかを再確認してください。

- **文字化けやエンコーディングエラー**  
  - JSON 化／読み込みは UTF-8 前提です。`electron-api.json` の文字コードを UTF-8 に統一してください。



## ライセンス

MIT License 

