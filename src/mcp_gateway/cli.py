import sys
import argparse
import asyncio
import logging
from mcp_gateway.core.registry import ToolRegistry
from mcp_gateway.backend.client import BackendClient
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
    parser = argparse.ArgumentParser(description="MCP Routing Gateway")
    parser.add_argument(
        "--config", 
        default="gateway_config.json", 
        help="Path to the gateway configuration JSON file (default: gateway_config.json)"
    )
    parser.add_argument(
        "--mcp-config",
        default="mcp_config.json",
        help="Path to the standard mcp_config.json file (default: mcp_config.json)"
    )
    args = parser.parse_args()

    logger.info(f"Starting MCP Routing Gateway. Loading config from {args.config}")
    
    # 1. Registry と Backend Client の初期化
    registry = ToolRegistry(args.config)
    backend_client = BackendClient(mcp_config_path=args.mcp_config)
    data_plane = DataPlaneServer(registry=registry, backend_client=backend_client)

    # 2. 非同期ループで通信を開始
    async def main_loop():
        # すべてのバックエンドサーバー(stdioプロセス)を起動
        await backend_client.start()
        
        # 起動した各サーバーからツール一覧を取得し、Registryを初期化(イミュータブル)
        backend_tools_map = {}
        for server_name in backend_client.sessions.keys():
            tools = await backend_client.fetch_tools(server_name)
            backend_tools_map[server_name] = tools
            
        registry.merge_and_resolve_tools(backend_tools_map)
        logger.info("Registry initialization complete. Ready to proxy requests.")
        
        try:
            # Data Plane のみ稼働(AIからのリクエストを待機)
            await data_plane.start()
        finally:
            # 終了時に必ずバックエンドプロセス群を安全に停止・クリーンアップする
            await backend_client.stop()

    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("Gateway stopped by user (KeyboardInterrupt).")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()