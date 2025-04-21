# ElectronRAG_MCP 仮想環境版

## 概要
このリポジトリは、Electron API ドキュメントをローカルで RAG（Retrieval-Augmented Generation）システムとして検索できる MCP サーバー／クライアント実装です。  


## 必要な作業
1. **仮想環境の作成 & 依存インストール**  
   ```bash
   python3 -m venv .venv
   # 仮想環境をアクティベート
   # Windows PowerShell: .\.venv\Scripts\Activate.ps1
   # macOS/Linux: source .venv/bin/activate
   pip install --upgrade pip setuptools
   pip install -r requirements.txt
   ```
2. **Electron ドキュメント JSON の生成（仮想環境内で実行）**  
   ```bash
   # docs-parser を仮想環境にインストール済み
   npx @electron/docs-parser --dir ./electron-repo/docs/api --moduleVersion 30.0.0 > electron-api.json
   ```
3. **LLM クライアントへの MCP 設定追加**  
   - 例：`claude_desktop_config.json` の `mcpServers` セクションに以下を追加  
     ```jsonc
     "ElectronRAG": {
       "command": "C:/path/to/ElectronRAG_MCP/.venv/Scripts/python.exe",
       "args": [
         "C:/path/to/ElectronRAG_MCP/server.py",
         "--json_path", "C:/path/to/ElectronRAG_MCP/electron-api.json",
         "--alpha", "0.7"
       ],
       "env": { "PYTHONPATH": "C:/path/to/ElectronRAG_MCP" }
     }
     ```
4. **クライアントの実行テスト（オプション）**  
   ```bash
   python auto_server_client.py
   ```

## ディレクトリ構成
```
ElectronRAG_MCP/
├── server.py                     ← MCP サーバー実装
├── auto_server_client.py         ← 自動起動クライアント（統合用）
├── requirements.txt              ← 必要パッケージ一覧
├── electron-api.json             ← 生成された Electron ドキュメント JSON
├── claude_desktop_config_sample.json  ← MCP 設定サンプル
└── README.md                     ← このファイル
```

## 使い方まとめ
1. リポジトリをクローンし、 `.venv` をセットアップ・アクティベート  
2. `requirements.txt` をインストール  
3. `npx @electron/docs-parser` で `electron-api.json` を作成  
4. LLM クライアントの設定ファイルに MCP エントリを追加  
5. クライアントからクエリを実行 → サーバーは自動で起動

---
