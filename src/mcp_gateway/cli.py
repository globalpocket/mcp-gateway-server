import sys
import argparse
import asyncio
import logging
from mcp_gateway.core.registry import ToolRegistry
from mcp_gateway.frontend.data_plane import DataPlaneServer

# 標準出力はAIエージェントとの通信（JSON-RPC）に占有されるため、
# アプリケーションのログはすべて標準エラー出力（stderr）に流す
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stderr)]
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="MCP Gateway Server")
    parser.add_argument(
        "--config", 
        default="gateway_config.yaml", 
        help="Path to the gateway configuration YAML file (default: gateway_config.yaml)"
    )
    args = parser.parse_args()

    logger.info(f"Starting MCP Gateway. Loading config from {args.config}")

    # 1. Registryの初期化と設定読み込み
    registry = ToolRegistry(args.config)
    
    # ※バックエンド実装前のため、動作確認用の一時的なモックデータを登録します
    mock_backend_tools = {
        "serverA": [
            {"name": "read_file", "description": "Read file from serverA", "inputSchema": {}},
            {"name": "run_command", "description": "Raw command on serverA", "inputSchema": {}}
        ],
        "serverB": [
            {"name": "search_github", "description": "Search Github on serverB", "inputSchema": {}}
        ]
    }
    logger.info("Merging tools from backend servers (Mock)...")
    registry.merge_and_resolve_tools(mock_backend_tools)

    # 2. Data Plane サーバーの初期化
    server = DataPlaneServer(registry=registry)

    # 3. 非同期ループで通信を開始
    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        logger.info("Gateway stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()