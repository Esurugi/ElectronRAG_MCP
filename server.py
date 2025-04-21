import os
import json
import time
import logging
import sys
import argparse

from mcp.server.fastmcp import FastMCP
from mcp import types
from src.utils.load_data import load_electron_api, chunk_electron_api
from src.search.hybrid_search import HybridSearcher

# ----- Logging Configuration -----
log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s"
)
file_handler = logging.FileHandler("server_debug.log", encoding="utf-8")
file_handler.setFormatter(log_formatter)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setFormatter(log_formatter)

logger = logging.getLogger("ElectronSearch")
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(stderr_handler)

# suppress verbose MCP logs
logging.getLogger("mcp").setLevel(logging.WARNING)

# ----- MCP Server Initialization -----
mcp = FastMCP("ElectronSearch")

# globals
searcher: HybridSearcher | None = None


def initialize_searcher(json_path: str, alpha: float, use_reranker: bool, use_rrf: bool) -> None:
    global searcher
    # load and chunk docs
    api_json = load_electron_api(json_path)
    chunks = chunk_electron_api(api_json)
    logger.info(f"Loaded {len(api_json)} modules and generated {len(chunks)} chunks")

    # init searcher
    searcher = HybridSearcher(
        documents=chunks,
        alpha=alpha,
        use_reranker=use_reranker,
        use_rrf=use_rrf
    )
    logger.info("Search engine initialized")


@mcp.tool()
def search_docs(keywords: list[str], top_k: int = 10) -> list[types.TextContent]:
    if searcher is None:
        err = "Searcher not initialized"
        logger.error(err)
        return [types.TextContent(type="text", text=json.dumps({"error": err}))]

    query = " ".join(keywords)
    logger.info(f"Received query: {query}")

    try:
        results = searcher.search(query, top_k=top_k)
        # format to dict list
        formatted = [
            {
                "type": doc.get("type", "unknown"),
                "name": doc.get("name", ""),
                "description": doc.get("description", ""),
                "content": doc.get("content", ""),
                "source": doc.get("source", ""),
                "score": float(doc.get("score", 0.0)),
            }
            for doc in results
        ]
        payload = json.dumps(formatted, ensure_ascii=False)
        return [types.TextContent(type="text", text=payload)]
    except Exception as e:
        logger.exception("Error during search")
        return [types.TextContent(type="text", text=json.dumps({"error": str(e)}))]


def main():
    parser = argparse.ArgumentParser(
        description="Electron API Documentation Search MCP Server"
    )
    parser.add_argument("--json_path", required=True, help="Path to electron-api.json")
    parser.add_argument("--alpha", type=float, default=0.7,
                        help="Alpha weight for vector vs keyword search (0.0-1.0)")
    parser.add_argument("--no_reranker", action="store_true",
                        help="Disable cross-encoder reranking")
    parser.add_argument("--no_rrf", action="store_true",
                        help="Disable RRF fusion")
    args = parser.parse_args()

    initialize_searcher(
        json_path=args.json_path,
        alpha=args.alpha,
        use_reranker=not args.no_reranker,
        use_rrf=not args.no_rrf,
    )

    logger.info("Starting MCP server...")
    mcp.run()


if __name__ == "__main__":
    main()
