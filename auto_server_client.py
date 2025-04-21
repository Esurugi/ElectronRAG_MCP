import os, argparse, asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--server_script", default="server.py")
    args = parser.parse_args()

    # 仮想環境の Python 実行ファイルを指定
    py = os.path.abspath(os.path.join(os.getcwd(), ".venv/Scripts/python.exe"))

    server_params = StdioServerParameters(
        command=py,                   # 仮想環境の python
        args=[args.server_script],
        env={"PYTHONPATH": os.getcwd()}  # プロジェクト直下を参照
    )

    async with stdio_client(server_params) as (r, w):
        async with ClientSession(r, w) as sess:
            await sess.initialize()
            # 例：ツール一覧を表示
            resp = await sess.list_tools()
            tools = [t for k, lst in resp if k=="tools" for t in lst]
            print("Tools:", [t.name for t in tools])

if __name__=="__main__":
    asyncio.run(main())