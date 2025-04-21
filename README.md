# ElectronRAG_MCP 仮想環境版

## 概要
このリポジトリは、Electron API ドキュメントをローカルでRAG（Retrieval-Augmented Generation）システムとして検索できるMCPサーバー／クライアント実装です。  
Python仮想環境を使用して依存関係を管理し、LLMクライアントからの自動起動をサポートします。

## 特徴
- Python仮想環境（venv）による依存パッケージの分離管理
- サーバー自動起動スクリプトによる簡単な統合
- Claude DesktopなどのLLMクライアントからのシームレスな利用

## ディレクトリ構成
```
ElectronRAG_MCP/
├── .venv/                    ← 仮想環境（セットアップ後に作成されます）
├── server.py                 ← MCPサーバー用スクリプト
├── auto_server_client.py     ← 自動起動クライアントスクリプト
├── test_client.py            ← 動作確認用クライアントスクリプト
├── requirements.txt          ← 必要パッケージ一覧
├── electron-api.json         ← Electron ドキュメントJSON
├── claude_desktop_config_sample.json  ← Claude Desktop設定例
└── README.md
```

## セットアップ手順

### 1. 仮想環境の作成と依存ライブラリのインストール

```bash
# プロジェクトルートで
python3 -m venv .venv

# 仮想環境を有効化
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# 依存パッケージをインストール
pip install --upgrade pip setuptools
pip install mcp[cli]==1.6.0 sentence-transformers faiss-cpu numpy tqdm python-dotenv pydantic requests uvicorn jsonpatch colorama
```

これで仮想環境内に必要なSDKや検索ライブラリがインストールされます。

### 2. Electron ドキュメント JSON の準備

公式ドキュメントを JSON 化して `electron-api.json` を用意します（すでにある場合はスキップ）。

```bash
# 必要に応じて一度だけ実行
npm install -g @electron/docs-parser
electron-docs-parser --dir ./electron-repo/docs/api --moduleVersion 30.0.0
```

### 3. クライアント動作確認

```bash
# 仮想環境が有効化されていることを確認
python auto_server_client.py
```

正常に動作すると、以下のように表示されます：
```
Tools: ['search_docs', 'search_with_japanese_query']
```

### 4. Claude Desktop などへの接続設定

1. **設定ファイルを開く**  
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`  
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`  

2. **mcpServers セクションに追記**

   ```jsonc
   {
     "mcpServers": {
       "ElectronRAG": {
         "command": "C:/path/to/ElectronRAG_MCP/.venv/Scripts/python.exe",
         "args": [
           "C:/path/to/ElectronRAG_MCP/server.py", 
           "--json_path", "C:/path/to/ElectronRAG_MCP/electron-api.json",
           "--alpha", "0.7"
         ],
         "env": {
           "PYTHONPATH": "C:/path/to/ElectronRAG_MCP"
         }
       }
     }
   }
   ```

   - `command`: 仮想環境のPython実行パスを絶対パスで指定
   - `args`: サーバースクリプトと必要なオプションを指定
   - `env.PYTHONPATH`: プロジェクトルートを指定

   > ⚠️ 注: 
   > - パスはOSに合わせて適切に指定してください。Windowsでは `\` を `/` に置き換える必要があります。
   > - 実際のパスは環境に合わせて絶対パスで指定してください。

3. **Claude Desktop を再起動**  
   「ElectronRAG」というサーバーが選択可能になります。

### 5. 他の LLM クライアントへの応用

- **Claude Code CLI**（`claude mcp add-json`）を使う場合も、同様の JSON を渡すだけで登録可能です。
  ```bash
  claude mcp add-json < claude_desktop_config_sample.json
  ```

## トラブルシューティング

- **venv/Scripts/python.exe が見つからない**  
  仮想環境が正しく作成されているか確認してください。

- **サーバーが起動しない**  
  - 仮想環境内に必要なパッケージがすべてインストールされているか確認
  - サーバースクリプトのパスが正しいか確認
  - `electron-api.json` のパスが正しいか確認

- **検索結果が空になる**  
  - インデックス作成が正常に完了しているか確認
  - キーワードが適切か確認

- **「Unexpected token 'G'...」エラーが表示される**
  - MCP プロトコルは標準出力（stdout）に純粋な JSON-RPC メッセージのみを期待しますが、
    サーバーが標準出力にログを出力すると JSON パースエラーが発生します
  - server.py では、すべてのログが標準エラー出力（stderr）に向くように設定されていることを確認してください

- **「Server disconnected」エラーが表示される**
  - サーバーが異常終了している可能性があります。以下を確認してください：
    1. ログファイル（server_debug.log）でエラーメッセージを確認
    2. 仮想環境のパスが正しいか確認
    3. Python のバージョンに互換性があるか確認（Python 3.8以上推奨）
    4. コマンドラインから直接サーバーを実行して詳細なエラーを確認：
       ```bash
       .\.venv\Scripts\python.exe server.py --json_path electron-api.json
       ```

## ライセンス
MIT License