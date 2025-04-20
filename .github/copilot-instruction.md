以下は、`electron-api-docs` への依存を完全に廃止し、公式の `@electron/docs-parser` のみを用いて Electron API ドキュメントを JSON 化し、MCP 経由でハイブリッド＋重み付け検索および再ランキングを実行する RAG システムの**完全版仕様書**です。

本仕様では、チャット上の日本語クエリを LLM が英語キーワードに変換し、MCP Python SDK の FastMCP で検索ツールを公開。ドキュメント取得には `@electron/docs-parser` を利用し、ベクトル検索（FAISS/Pinecone）と BM25 キーワード検索を Pinecone の `alpha` パラメータや Reciprocal Rank Fusion で融合、さらに SentenceTransformers の Cross‑Encoder で再ランキングを行い、最終結果を LLM に渡して高精度な回答生成を実現します。

---

## ① 機能要求

**機能要求概説**
1.MCPサーバーとして動作するシステム
2.LLMクライアント（Claude Desktop等）から検索リクエストを受け取る
3.Electronドキュメントのデータに対してRAG検索を実行
4.結果をMCPプロトコル経由でLLMに返す

1. **日本語チャットインターフェース**  
   Claude Desktop 等のチャットクライアントで日本語クエリを受け取り、LLM が検索キーワードを英語で生成する。 

2. **MCP 通信**  
   公式 Python SDK (`mcp[cli]`) に統合された `FastMCP` を用い、`@mcp.tool()` デコレータでハイブリッド検索ツールを公開し、STDIO 経由でチャットクライアントと通信する。

3. **ドキュメント JSON 化**  
   `@electron/docs-parser` v2.0.0 を CLI で実行し、最新の Markdown ドキュメントを損失なく構造化 JSON (`electron-api.json`) に変換する。 

4. **ハイブリッド＋重み付け検索**  
   - **ベクトル検索**：FAISS（ローカル）または Pinecone（クラウド）でセマンティック検索を実行  
   - **キーワード検索**：Elasticsearch BM25 による正確な語彙マッチングを実行  
   - Pinecone の `alpha` パラメータで両者を 0〜1 の比率で融合し、必要に応じて Reciprocal Rank Fusion で順位を更に最適化する。 

5. **再ランキング（オプション）**  
   上位候補（概ね上位 50 件程度）を SentenceTransformers の Cross‑Encoder モデルでペアワイズ再スコアリングし、微細な関連度差を反映した最終順位を生成する。 

6. **LLM へのコンテキスト提供**  
   最終上位 N 件のドキュメントをチャット LLM にペイロードとして渡し、回答生成や詳細解説に活用する。

---

## ② 使用技術

- **ドキュメント変換**  
  - `@electron/docs-parser` v2.0.0：公式ツールで Markdown → JSON 変換 

- **プロトコル連携**  
  - MCP Python SDK (`mcp[cli]`)：FastMCP 統合済みで簡潔にサーバー構築が可能

- **セマンティック検索**  
  - **FAISS**：ローカルで高速埋め込み検索。`IndexFlatL2` などチューニングガイドあり
  - **Pinecone**：マネージドクラウドベクトルストア。`alpha` 重み調整対応 

- **キーワード検索**  
  - **Elasticsearch BM25**：デフォルトの類似性スコアリングアルゴリズム。パラメータ `k1` や `b` 調整可能 

- **重み付けハイブリッド検索**  
  - **PineconeHybridSearchRetriever**（LangChain 統合）で `alpha` 指定  
  - **RRF**：Reciprocal Rank Fusion アルゴリズムで複数ランクを融合 

- **再ランキング**  
  - **Cross‑Encoder**：`cross-encoder/ms-marco-MiniLM-L-6-v2` 等を利用 
- **フレームワーク**  
  - **LangChain**：RAG パイプライン統合  
  - **WeaviateHybridSearchRetriever**（オプション） 

- **チャットクライアント**  
  - Claude Desktop（MCP クライアント）  

---

## ③ 要件定義

### 機能要件

| ID   | 要件                             | 詳細                                                                             |
|------|----------------------------------|----------------------------------------------------------------------------------|
| FR1  | キーワード生成                   | 日本語質問から LLM が適切な英語検索キーワードを生成                               |
| FR2  | MCP ツール公開                   | `@mcp.tool()` デコレータで `search_docs(keywords: list[str])` を公開            |
| FR3  | JSON ドキュメント生成            | `electron-docs-parser` で `electron-api.json` を出力                            |
| FR4  | ハイブリッド＋重み付け検索       | FAISS/Pinecone + BM25 を並列実行し、`alpha`／RRF で融合                           |
| FR5  | 再ランキングオプション           | Cross‑Encoder による再スコアリングを実行可能                                     |
| FR6  | コンテキスト生成                 | 上位 N 件を LLM ペイロードとして渡し、回答生成                                    |

### 非機能要件

| ID    | 要件              | 詳細                                     |
|-------|-------------------|------------------------------------------|
| NFR1  | レイテンシ        | 検索 → 結果取得まで 500ms 以下           |
| NFR2  | 同時処理数        | 同時 10 セッションまで安定稼働          |
| NFR3  | 保守性            | ドキュメント更新後、即時 JSON 化可能     |
| NFR4  | セキュリティ      | MCP 通信はローカル TLS/SPDY 等で閉域化   |

---

## ④ 参照ソース
1. **MCP Python SDK** – FastMCP 統合および使用例   
2. **FastMCP v1.2.0 リリース** – `mcp[cli]>=1.2.0` で FastMCP 統合済み   
3. **@electron/docs-parser v2.0.0** – Markdown→JSON 変換ツール   
4. **FAISS ベストプラクティス** – IndexFlatL2 などの選定ガイド   
5. **Pinecone Hybrid Search** – `alpha` パラメータ解説   
6. **Elasticsearch BM25** – アルゴリズムと変数の解説 
7. **LangChain PineconeHybridSearchRetriever** – `alpha` 設定方法 
8. **RRF (Reciprocal Rank Fusion)** – Azure AI Search 事例 
9. **SentenceTransformers Cross‑Encoder** – 再ランキングモデル API リファレンス 
10. **Weaviate Hybrid Search** – dense＋sparse 融合 

---

## ⑤ コーディング規約／推奨例

### 5.1 MCP ツール実装

```python
# server.py
from mcp.server.fastmcp import FastMCP  # 公式 SDK 統合済み

mcp = FastMCP("ElectronSearch")  # サービス名

@mcp.tool()
def search_docs(keywords: list[str]) -> list[dict]:
    """
    ハイブリッド検索を実行し、
    Electron API JSON からマッチ結果を返す。
    """
    return perform_hybrid_search(keywords)

if __name__ == "__main__":
    mcp.serve()  # STDIO 経由でチャットクライアントと通信
```


### 5.2 ドキュメントパース

```bash
# 最新の公式ドキュメントを JSON に変換
npm install -g @electron/docs-parser
electron-docs-parser \
  --source path/to/electron/docs/api \
  --out ./electron-api.json
```


### 5.3 重み付けハイブリッド検索

```python
from langchain_community.retrievers import PineconeHybridSearchRetriever
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
retriever = PineconeHybridSearchRetriever(
    index=pinecone_index,
    embeddings=model,
    alpha=0.7  # Dense:Sparse = 70:30
)

docs = retriever.get_relevant_documents("BrowserWindow openDevTools")
```


### 5.4 再ランキング

```python
from sentence_transformers.cross_encoder import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
reranked = sorted(
    docs,
    key=lambda d: reranker.predict([(query, d.page_content)]),
    reverse=True
)[:10]
```


---


以下は、「1タスク＝1処理」の粒度で分解した実装ワークフローです。各タスクには、参照すべき公式ドキュメントへのリンクを示す引用を付与しています。

---

## ワークフロー一覧

1. **ローカルに Electron ドキュメントをクローン**  
   - GitHub から公式リポジトリをクローンし、`docs/api` ディレクトリを準備します。   

2. **`@electron/docs-parser` インストール**  
   - npm または UV で `@electron/docs-parser` v2.0.0 をインストールします。  
     ```bash
     npm install -g @electron/docs-parser
     # または
     uv add "@electron/docs-parser"
     ```   

3. **JSON 化スクリプト実行**  
   - クローン済みドキュメントを対象に `electron-docs-parser --source docs/api --out electron-api.json` を実行し、構造化 JSON を生成します。   

4. **Python プロジェクト初期化**  
   - `python-sdk`（MCP Python SDK）をインストールし、仮想環境を作成します。  
     ```bash
     uv add "mcp[cli]>=1.2.0"
     # または
     pip install "mcp[cli]>=1.2.0"
     ```

5. **`server.py` のスキャフォールディング**  
   - プロジェクトルートに `server.py` を作成し、`from mcp.server.fastmcp import FastMCP` を追加します。   

6. **MCP ツール定義**  
   - `@mcp.tool()` デコレータで `search_docs(keywords: list[str])` 関数を定義し、後続検索処理を呼び出せるようにします。   

7. **JSON ロード機能の実装**  
   - `electron-api.json` を Python で読み込み、チャンク（モジュール・クラス・メソッド単位）に分割する処理を実装します。   

8. **BM25 インデックス構築**  
   - Elasticsearch または Whoosh で BM25 インデックスを作成し、ドキュメントの `name`／`description` フィールドを投入します。   

9. **セマンティック埋め込み生成**  
   - `sentence-transformers/all-MiniLM-L6-v2` で各チャンクの埋め込みを生成する関数を実装します。   

10. **ベクトルストア構築（FAISS/Pinecone）**  
    - ローカル高速検索なら FAISS で `IndexFlatL2` を、クラウド利用なら Pinecone index を構築します。   

11. **重み付けハイブリッド検索処理**  
    - LangChain の `PineconeHybridSearchRetriever(alpha=0.7)` や自前実装で、ベクトル結果と BM25 結果を融合します。   

12. **Reciprocal Rank Fusion (RRF) 実装**  
    - RRF アルゴリズムを用意し、両検索結果のリストを融合して最終スコアを計算する関数を実装します。   

13. **再ランキング（Cross‑Encoder）実装**  
    - 上位候補を `CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")` でスコア再計算し、精度を向上させます。   

14. **LLM への入力コンテキスト組成**  
    - 再ランキング後の上位 N 件をまとめ、LLM プロンプト用のコンテキスト文字列に整形します。   

15. **MCP サーバー起動コード実装**  
    - `if __name__ == "__main__": mcp.serve()` を追加し、STDIO 経由で Claude Desktop 等と接続します。   

16. **単体テスト作成**  
    - 各処理（JSONロード、BM25検索、ベクトル検索、融合、再ランキング）のユニットテストを作成します。   

17. **統合テスト／MCP Inspector で動作確認**  
    - `mcp dev server.py` や Claude Desktop からキーワード検索を試し、期待通り動作するか確認します。   

18. **デプロイ＆ドキュメント化**  
    - pyinstaller などでバイナリ化し、README にワークフローを記載して社内共有します。   

---
