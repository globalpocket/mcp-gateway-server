import pytest
import asyncio
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from mcp_gateway.frontend.data_plane import DataPlaneServer

@pytest.mark.anyio
async def test_data_plane_start_eof():
    """標準入力がEOFを返した際のループ終了処理を網羅"""
    server = DataPlaneServer(registry=MagicMock())
    
    # 読み取り可能なデータがない(EOF)状態をシミュレート
    mock_reader = AsyncMock()
    mock_reader.readline.return_value = b"" # EOF
    
    with patch("asyncio.StreamReader", return_value=mock_reader):
        with patch("asyncio.get_running_loop", return_value=AsyncMock()):
            # start() が無限ループせず、EOFで即座に終了することを確認
            await asyncio.wait_for(server.start(), timeout=0.1)

@pytest.mark.anyio
async def test_data_plane_internal_error_handling(capsys):
    """ロジック内部で予期せぬ例外が発生した際のエラー応答を網羅"""
    # 取得時に意図的に例外を投げるRegistryを渡す
    mock_registry = MagicMock()
    mock_registry.get_tool_routing_info.side_effect = Exception("Crash Test")
    
    server = DataPlaneServer(registry=mock_registry)
    req = '{"jsonrpc": "2.0", "id": "err-1", "method": "tools/call", "params": {"name": "any"}}'
    
    await server._handle_message(req)
    
    captured = capsys.readouterr()
    # Internal error (-32603) が返ることを確認
    assert '"code": -32603' in captured.out
    assert "Internal error: Crash Test" in captured.out