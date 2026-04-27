import pytest
import json
from unittest.mock import MagicMock
from mcp_gateway.frontend.data_plane import DataPlaneServer

@pytest.mark.anyio
async def test_handle_message_parse_error(capsys):
    """壊れたJSONを送った際の JSONDecodeError 応答を網羅"""
    server = DataPlaneServer(registry=MagicMock())
    await server._handle_message("invalid json{")
    
    captured = capsys.readouterr()
    # JSON-RPC Parse error (-32700) が返ることを確認
    assert '"code": -32700' in captured.out
    assert '"message": "Parse error"' in captured.out

@pytest.mark.anyio
async def test_handle_message_method_not_found(capsys):
    """存在しないメソッドを呼ばれた際のエラー応答を網羅"""
    server = DataPlaneServer(registry=MagicMock())
    # 存在しないメソッド 'unknown/method' をリクエスト
    req = json.dumps({"jsonrpc": "2.0", "id": 99, "method": "unknown/method"})
    await server._handle_message(req)
    
    captured = capsys.readouterr()
    # Method not found (-32601) が返ることを確認
    assert '"code": -32601' in captured.out
    assert "Method not found" in captured.out

@pytest.mark.anyio
async def test_handle_message_ping(capsys):
    """ping メソッドに対して正しく空のレスポンスを返すか検証"""
    server = DataPlaneServer(registry=MagicMock())
    # ping をリクエスト
    req = json.dumps({"jsonrpc": "2.0", "id": "ping-test", "method": "ping"})
    await server._handle_message(req)
    
    captured = capsys.readouterr()
    # 空の result ({}) が返ることを確認
    assert '"id": "ping-test"' in captured.out
    assert '"result": {}' in captured.out