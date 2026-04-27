import pytest
import json
import time
from unittest.mock import MagicMock, AsyncMock, patch
from mcp_gateway.frontend.data_plane import DataPlaneServer

@pytest.mark.anyio
async def test_sampling_reverse_routing():
    """バックエンドからのリクエストIDを記録し、AIのレスポンスを正しく送り返すかを網羅"""
    mock_client = MagicMock()
    mock_client.forward_request = AsyncMock()
    
    server = DataPlaneServer(registry=MagicMock(), backend_client=mock_client)
    
    # 1. バックエンドからLLMへの要求を受信したと想定し、IDを記録させる
    backend_req = json.dumps({"jsonrpc": "2.0", "id": "sample-123", "method": "sampling/createMessage"})
    server._handle_backend_message(backend_req, "/mcp/serverA")
    assert "sample-123" in server._response_routes
    assert server._response_routes["sample-123"]["route"] == "/mcp/serverA"
    
    # 2. AIからの応答を処理させる
    ai_response = json.dumps({"jsonrpc": "2.0", "id": "sample-123", "result": {"content": "Hello"}})
    await server._handle_message(ai_response)
    
    # 3. 正しいバックエンドに転送されたか検証
    mock_client.forward_request.assert_called_once()
    called_route, payload = mock_client.forward_request.call_args[0]
    assert called_route == "/mcp/serverA"
    assert payload["result"]["content"] == "Hello"
    
    # 4. 未知のIDへの応答が来た場合のWarningパス
    ai_unknown = json.dumps({"jsonrpc": "2.0", "id": "unknown-999", "result": {"content": "Who?"}})
    await server._handle_message(ai_unknown)
    assert mock_client.forward_request.call_count == 1 # 呼び出し回数が増えていないことを確認

def test_sampling_memory_leak_protection():
    """メモリリーク対策（タイムアウトと上限サイズ）が機能するか検証"""
    server = DataPlaneServer(registry=MagicMock())
    
    # 意図的に上限サイズを小さくしてテスト
    server.MAX_ROUTES = 2
    server.ROUTE_TIMEOUT = 10
    
    # 1. 上限サイズの検証 (LRU方式)
    server._handle_backend_message(json.dumps({"jsonrpc": "2.0", "id": "id1", "method": "m"}), "/r1")
    server._handle_backend_message(json.dumps({"jsonrpc": "2.0", "id": "id2", "method": "m"}), "/r2")
    server._handle_backend_message(json.dumps({"jsonrpc": "2.0", "id": "id3", "method": "m"}), "/r3")
    
    # 上限2なので、最初の id1 が消えて id2, id3 だけが残るはず
    assert "id1" not in server._response_routes
    assert "id2" in server._response_routes
    assert "id3" in server._response_routes
    
    # 2. タイムアウトの検証
    # time.time() をモックして時間を進める
    with patch("time.time", return_value=time.time() + 20):
        # 新しいメッセージが来たタイミングでクリーンアップが走る
        server._handle_backend_message(json.dumps({"jsonrpc": "2.0", "id": "id4", "method": "m"}), "/r4")
        
        # 以前の id2, id3 はタイムアウトで消え、id4 だけが残る
        assert "id2" not in server._response_routes
        assert "id3" not in server._response_routes
        assert "id4" in server._response_routes