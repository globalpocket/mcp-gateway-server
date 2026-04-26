import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from mcp_gateway.core.registry import ToolRegistry

logger = logging.getLogger(__name__)

class DataPlaneServer:
    """
    AIエージェントと標準入出力(stdio)経由でJSON-RPC通信を行うサーバー
    """
    def __init__(self, registry: ToolRegistry, backend_client: Any = None):
        self.registry = registry
        # ※バックエンドクライアントは次のステップで実装します
        self.backend_client = backend_client 
        self._running = False

    async def start(self):
        """標準入力からのJSON-RPCリクエストを非同期で待ち受けるループ"""
        self._running = True
        logger.info("Data Plane Server started. Listening on stdio...")
        
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        while self._running:
            try:
                line = await reader.readline()
                if not line:
                    break # EOF (AIエージェントからの接続切断)
                
                await self._handle_message(line.decode('utf-8').strip())
            except Exception as e:
                logger.error(f"Error reading from stdin: {e}")

    async def _handle_message(self, message: str):
        """受信したJSON-RPCメッセージを解析してルーティングする"""
        if not message:
            return

        try:
            req = json.loads(message)
            req_id = req.get("id")
            method = req.get("method")
            params = req.get("params", {})

            # MCPプロトコルの主要メソッドのルーティング
            if method == "initialize":
                await self._send_response(req_id, self._handle_initialize())
            
            elif method == "tools/list":
                await self._send_response(req_id, self._handle_tools_list())
            
            elif method == "tools/call":
                result = await self._handle_tools_call(params.get("name"), params.get("arguments", {}))
                await self._send_response(req_id, result)
                
            # 通知（Notifications）等の処理はスキップ（idがない場合はレスポンス不要）
            elif req_id is not None:
                await self._send_error(req_id, -32601, f"Method not found: {method}")

        except json.JSONDecodeError:
            await self._send_error(None, -32700, "Parse error")
        except Exception as e:
            logger.error(f"Internal error handling message: {e}")
            await self._send_error(req.get("id"), -32603, f"Internal error: {str(e)}")

    def _handle_initialize(self) -> Dict[str, Any]:
        """初期化リクエストへの応答 (Gatewayとしてのケーパビリティを返す)"""
        return {
            "protocolVersion": "2024-11-05", # MCPのプロトコルバージョン
            "capabilities": {
                "tools": {} # ツール提供機能があることを宣言
            },
            "serverInfo": {
                "name": "mcp-gateway-server",
                "version": "0.1.0"
            }
        }

    def _handle_tools_list(self) -> Dict[str, Any]:
        """AIエージェントに提供可能なツール一覧を返す"""
        tools = self.registry.get_tools_for_llm()
        return {"tools": tools}

    async def _handle_tools_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """バックエンドへのツール実行リクエストのプロキシ処理"""
        routing_info = self.registry.get_tool_routing_info(tool_name)
        
        if not routing_info:
            # 存在しないツールの呼び出し
            return {
                "content": [{"type": "text", "text": f"Error: Tool '{tool_name}' not found."}],
                "isError": True
            }

        # TODO: 次のステップで、ここで HTTP/SSE 経由でバックエンドの Kong にリクエストを投げる処理を実装します。
        # 今回はモックの応答を返します。
        target_route = routing_info["target_route"]
        return {
            "content": [{"type": "text", "text": f"[Mock] Forwarded call for '{tool_name}' to {target_route} with args: {arguments}"}],
            "isError": False
        }

    async def _send_response(self, req_id: Any, result: Dict[str, Any]):
        """JSON-RPCの成功レスポンスを標準出力へ書き込む"""
        if req_id is None:
            return
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result
        }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()

    async def _send_error(self, req_id: Any, code: int, message: str):
        """JSON-RPCのエラーレスポンスを標準出力へ書き込む"""
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": code, "message": message}
        }
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()