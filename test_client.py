import os
import io
import json
import argparse
import asyncio
from typing import List, Dict, Any

# StdioServerParametersをmcp直下からインポート
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_search(session: ClientSession, keywords: List[str], top_k: int = 5):
    """
    MCPサーバーに接続して検索を実行するテスト関数です。
    
    Args:
        session (ClientSession): MCP クライアントセッション
        keywords (List[str]): 検索キーワードのリスト
        top_k (int): 返す結果の数
    """
    try:
        # 利用可能ツールの確認
        tools_response = await session.list_tools()
        tools = [t for key, lst in tools_response if key == "tools" for t in lst]
        print("利用可能なツール:", [tool.name for tool in tools])

        # 検索実行
        print(f"\n検索キーワード: {keywords}")
        response = await session.call_tool("search_docs", {"keywords": keywords, "top_k": top_k})
        
        # TextContentからJSON文字列を取得
        content = response.content  # List[TextContent]
        if not content:
            print("結果が空です")
            return
        
        # 最初のTextContentオブジェクトからテキストを取得
        text_content = content[0]
        
        # JSONパース（サーバーからJSON文字列が返される前提）
        try:
            results = json.loads(text_content.text)
            
            print(f"{len(results)}件の結果が見つかりました:\n")
            for i, result in enumerate(results, 1):
                # JSONから直接辞書としてアクセス
                name = result["name"]
                score = result["score"]
                result_type = result["type"]
                description = result["description"]
                source = result["source"]
                
                print(f"{i}. {name} (スコア: {score:.4f})")
                print(f"   種類: {result_type}")
                print(f"   説明: {description[:100]}..." if len(description) > 100 else f"   説明: {description}")
                print(f"   出典: {source}\n")
        except json.JSONDecodeError:
            print("JSONパースエラー。サーバーからの応答をそのまま表示します:")
            print(text_content.text)
        except KeyError as e:
            print(f"応答データに必要なキーがありません: {e}")
            print(f"応答データ: {results}")
    
    except Exception as e:
        print(f"検索実行中に予期せぬエラーが発生: {e}")
        import traceback
        traceback.print_exc()
        return


async def test_japanese_search(session: ClientSession, query: str, top_k: int = 5):
    """
    MCPサーバーに接続して日本語検索を実行するテスト関数です。
    
    Args:
        session (ClientSession): MCP クライアントセッション
        query (str): 日本語検索クエリ
        top_k (int): 返す結果の数
    """
    try:
        # 日本語検索を実行
        print(f"\n日本語検索クエリ: {query}")
        print(f"検索結果の上位{top_k}件を取得します...\n")
        
        response = await session.call_tool("search_with_japanese_query", {"query": query, "top_k": top_k})
        
        # TextContentからJSON文字列を取得
        content = response.content  # List[TextContent]
        if not content:
            print("結果が空です")
            return
        
        # 最初のTextContentオブジェクトからテキストを取得
        text_content = content[0]
        
        # JSONパース（サーバーからJSON文字列が返される前提）
        try:
            results = json.loads(text_content.text)
            
            print(f"{len(results)}件の結果が見つかりました:\n")
            for i, result in enumerate(results, 1):
                # JSONから直接辞書としてアクセス
                name = result["name"]
                score = result["score"]
                result_type = result["type"]
                description = result["description"]
                source = result["source"]
                
                print(f"{i}. {name} (スコア: {score:.4f})")
                print(f"   種類: {result_type}")
                print(f"   説明: {description[:100]}..." if len(description) > 100 else f"   説明: {description}")
                print(f"   出典: {source}\n")
        except json.JSONDecodeError:
            print("JSONパースエラー。サーバーからの応答をそのまま表示します:")
            print(text_content.text)
        except KeyError as e:
            print(f"応答データに必要なキーがありません: {e}")
            print(f"応答データ: {results}")
    
    except Exception as e:
        print(f"日本語検索実行中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return


async def main():
    """
    MCPクライアントを起動し、テストを実行します。
    """
    parser = argparse.ArgumentParser(description="Test MCP client for Electron API Search")
    parser.add_argument("--keywords", nargs='+', help="Keywords for search", default=["window", "create"])
    parser.add_argument("--japanese", type=str, help="Japanese query", default="ウィンドウを作成する方法")
    parser.add_argument("--top_k", type=int, help="Number of results to return", default=5)
    parser.add_argument("--mode", choices=["english", "japanese", "both"], default="both", help="Search mode")
    parser.add_argument("--server_script", type=str, default="server.py", help="Server script path")
    
    args = parser.parse_args()
    
    try:
        # サーバーパラメータを設定
        server_path = os.path.abspath(args.server_script)
        server_params = StdioServerParameters(
            command="python",
            args=[server_path],
            env=None,  # 現在の環境変数を使用
        )
        
        print(f"MCPサーバーに接続しています: {args.server_script}")
        
        # stdio_clientで標準入出力ストリームを取得
        async with stdio_client(server_params) as (rb, wb):
            # テキストラッピングを使用せず、ストリームを直接使用
            async with ClientSession(rb, wb) as session:
                # セッション初期化
                await session.initialize()
                print("MCPサーバーに接続しました\n")
                
                # 検索モードに応じてテスト実行
                if args.mode in ["english", "both"]:
                    await test_search(session, args.keywords, args.top_k)
                
                if args.mode in ["japanese", "both"]:
                    await test_japanese_search(session, args.japanese, args.top_k)
    
    except Exception as e:
        print(f"MCPクライアントの実行中にエラーが発生しました: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())