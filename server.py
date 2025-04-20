import os
import json
import time
import logging
from typing import List, Dict, Any, Optional
import argparse

from mcp.server.fastmcp import FastMCP
from mcp import types
from src.utils.load_data import load_electron_api, chunk_electron_api
from src.search.hybrid_search import HybridSearcher

# ログ設定
logging.basicConfig(
    filename='server_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# MCP サーバーの初期化
mcp = FastMCP("ElectronSearch")

# グローバル変数
searcher = None
electron_api_chunks = None


def initialize_searcher(
    json_path: Optional[str] = None,
    alpha: float = 0.7,
    use_reranker: bool = True,
    use_rrf: bool = True
) -> HybridSearcher:
    """
    検索エンジンを初期化します。
    
    Args:
        json_path (str): Electron API JSONファイルのパス
        alpha (float): ベクトル検索とキーワード検索の重み付け
        use_reranker (bool): 再ランキングを使用するかどうか
        use_rrf (bool): 結果融合にRRFを使用するかどうか
    
    Returns:
        HybridSearcher: 初期化された検索エンジン
    """
    global electron_api_chunks, searcher  # searcher変数をグローバル宣言
    
    # Electron API JSONの読み込み
    api_json = load_electron_api(json_path)
    logger.info(f"Loaded Electron API JSON with {len(api_json)} modules")
    print(f"Loaded Electron API JSON with {len(api_json)} modules")
    
    # チャンキング
    start_time = time.time()
    electron_api_chunks = chunk_electron_api(api_json)
    logger.info(f"Generated {len(electron_api_chunks)} chunks in {time.time() - start_time:.2f} seconds")
    print(f"Generated {len(electron_api_chunks)} chunks in {time.time() - start_time:.2f} seconds")
    
    # 検索エンジンの初期化
    start_time = time.time()
    searcher = HybridSearcher(
        documents=electron_api_chunks,
        alpha=alpha,
        use_reranker=use_reranker,
        use_rrf=use_rrf
    )
    logger.info(f"Initialized search engine in {time.time() - start_time:.2f} seconds")
    print(f"Initialized search engine in {time.time() - start_time:.2f} seconds")
    
    return searcher


@mcp.tool()
def search_docs(keywords: List[str], top_k: int = 10):
    """
    Electron APIドキュメントを検索します。
    
    Args:
        keywords (List[str]): 検索キーワードのリスト
        top_k (int): 返す結果の最大数
        
    Returns:
        TextContent: 検索結果を含むJSONテキスト
    """
    global searcher
    
    try:
        # キーワードを連結して検索クエリを作成
        query = " ".join(keywords)
        logger.info(f"検索クエリ: '{query}'")
        
        if searcher is None:
            logger.error("searcher が初期化されていません")
            return []
        
        # 検索を実行
        results = searcher.search(query, top_k=top_k)
        logger.info(f"{len(results)}件の結果が見つかりました")
        
        # 結果内容をログに記録
        for i, doc in enumerate(results[:3]):  # 最初の3件だけログ記録
            logger.debug(f"結果{i+1}: {type(doc)}")
            logger.debug(f"  name: {doc.get('name', 'なし')}")
            logger.debug(f"  type: {doc.get('type', 'なし')}")
            logger.debug(f"  score: {doc.get('score', 0.0)}")
        
        # 結果を完全なシンプルな辞書のリストとして整形
        formatted_results = []
        for doc in results:
            # 必要な情報だけを含む新しい辞書を作成
            formatted_doc = {
                "type": str(doc.get("type", "unknown")), 
                "name": str(doc.get("name", "")),
                "description": str(doc.get("description", "")),
                "content": str(doc.get("content", "")),
                "source": str(doc.get("source", "")),
                "score": float(doc.get("score", 0.0))
            }
            formatted_results.append(formatted_doc)
        
        logger.info(f"結果を{len(formatted_results)}件返します")
        if formatted_results:
            logger.debug(f"最初の結果: {formatted_results[0]}")
        
        # JSON文字列に変換して返す
        json_text = json.dumps(formatted_results, ensure_ascii=False)
        return [types.TextContent(text=json_text, type="text")]
        
    except Exception as e:
        logger.exception(f"検索実行中にエラー発生: {e}")
        return [types.TextContent(text=json.dumps({"error": str(e)}), type="text")]


@mcp.tool()
def search_with_japanese_query(query: str, top_k: int = 10):
    """
    日本語クエリをLLMが英語キーワードに変換し、Electron APIドキュメントを検索します。
    MCP経由でLLMが英語キーワードに変換する機能を内部で使用します。
    
    Args:
        query (str): 日本語の検索クエリ
        top_k (int): 返す結果の最大数
    
    Returns:
        TextContent: 検索結果を含むJSONテキスト
    """
    # 注意: この関数はMCPで統合された場合にLLMが適切な英語キーワードを生成することを期待しています。
    # 実際のLLMによる処理はこの関数内では実装されていません。
    # MCP統合環境でLLMがこの日本語クエリを解釈して適切な英語キーワードを生成します。
    
    # LLMが生成した英語キーワードで検索（MCP経由で実装）
    logger.info(f"日本語クエリ: {query}")
    keywords = [query]  # ここではそのままクエリを使用。MCPでLLMが処理します。
    return search_docs(keywords, top_k)


def main():
    """
    MCPサーバーを起動します。
    """
    parser = argparse.ArgumentParser(description="Electron API Documentation Search with MCP")
    parser.add_argument("--json_path", type=str, help="Path to the Electron API JSON file")
    parser.add_argument("--alpha", type=float, default=0.7, help="Weight for vector vs keyword search (0.0 to 1.0)")
    parser.add_argument("--no_reranker", action="store_true", help="Disable reranking")
    parser.add_argument("--no_rrf", action="store_true", help="Disable RRF fusion")
    
    args = parser.parse_args()
    
    # 検索エンジンを初期化
    global searcher
    logger.info("検索エンジンを初期化します")
    searcher = initialize_searcher(
        json_path=args.json_path,
        alpha=args.alpha,
        use_reranker=not args.no_reranker,
        use_rrf=not args.no_rrf
    )
    
    # MCPサーバーを起動
    logger.info("MCPサーバーを起動します")
    print("Starting MCP server for Electron API documentation search...")
    # mcp.serve() の代わりにrunを使用
    mcp.run()


if __name__ == "__main__":
    main()