import pytest
import sys
import asyncio
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from mcp_gateway.cli import main

def test_cli_fatal_error_exit():
    """Fatal error発生時に sys.exit(1) が呼ばれることを確認"""
    with patch("argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = MagicMock(work_dir="~/.mcp-routing-gateway", config="gateway_config.json", mcp_config="mcp_config.json")
        
        # モックした asyncio.run に渡されたコルーチンを安全に閉じてから例外を発生させる
        def mock_run_fatal(coro):
            coro.close()
            raise Exception("Fatal Error")
            
        with patch("asyncio.run", side_effect=mock_run_fatal):
            with pytest.raises(SystemExit) as e:
                main()
            
            # 終了ステータスが 1 であることを検証
            assert e.value.code == 1

def test_cli_keyboard_interrupt():
    """KeyboardInterrupt発生時に正常終了することを確認"""
    with patch("argparse.ArgumentParser.parse_args") as mock_args:
        mock_args.return_value = MagicMock(work_dir="~/.mcp-routing-gateway", config="gateway_config.json", mcp_config="mcp_config.json")
        
        # モックした asyncio.run に渡されたコルーチンを安全に閉じてから例外を発生させる
        def mock_run_kb(coro):
            coro.close()
            raise KeyboardInterrupt()
            
        with patch("asyncio.run", side_effect=mock_run_kb):
            # SystemExit が発生せず、関数が正常にリターンすることを検証
            main()

def test_cli_path_resolution_relative():
    """ワーキングディレクトリを基準に相対パスが正しく解決されることを確認"""
    with patch("argparse.ArgumentParser.parse_args") as mock_args, \
         patch("mcp_gateway.cli.ToolRegistry") as mock_registry_cls, \
         patch("mcp_gateway.cli.BackendClient") as mock_backend_cls, \
         patch("mcp_gateway.cli.DataPlaneServer"):
         
        # コルーチンがawaitされずに破棄される警告を防ぐため、モックで確実に閉じる
        def mock_run_close(coro):
            coro.close()
            
        with patch("asyncio.run", side_effect=mock_run_close):
            # モック引数の設定
            mock_args.return_value = MagicMock(
                work_dir="~/.mcp-routing-gateway",
                config="gateway_config.json",
                mcp_config="mcp_config.json"
            )
            
            main()
            
            # 期待されるパスの計算
            expected_work_dir = Path("~/.mcp-routing-gateway").expanduser().resolve()
            expected_config = (expected_work_dir / "gateway_config.json").resolve()
            expected_mcp_config = (expected_work_dir / "mcp_config.json").resolve()
            
            # 初期化時に正しい絶対パスが渡されているか検証
            mock_registry_cls.assert_called_once_with(str(expected_config))
            mock_backend_cls.assert_called_once_with(mcp_config_path=str(expected_mcp_config))

def test_cli_path_resolution_absolute():
    """設定ファイルに絶対パスが指定された場合は、work_dirに依存せずそのまま使われるか確認"""
    with patch("argparse.ArgumentParser.parse_args") as mock_args, \
         patch("mcp_gateway.cli.ToolRegistry") as mock_registry_cls, \
         patch("mcp_gateway.cli.BackendClient") as mock_backend_cls, \
         patch("mcp_gateway.cli.DataPlaneServer"):
         
        # コルーチンがawaitされずに破棄される警告を防ぐため、モックで確実に閉じる
        def mock_run_close(coro):
            coro.close()
            
        with patch("asyncio.run", side_effect=mock_run_close):
            absolute_config = "/absolute/path/gateway_config.json"
            absolute_mcp_config = "/absolute/path/mcp_config.json"
            
            # モック引数の設定 (絶対パスを渡す)
            mock_args.return_value = MagicMock(
                work_dir="~/.mcp-routing-gateway",
                config=absolute_config,
                mcp_config=absolute_mcp_config
            )
            
            main()
            
            # 初期化時にそのまま絶対パスが渡されているか検証 (osの違いを吸収するためresolveを通す)
            expected_config = str(Path(absolute_config).resolve())
            expected_mcp_config = str(Path(absolute_mcp_config).resolve())
            
            mock_registry_cls.assert_called_once_with(expected_config)
            mock_backend_cls.assert_called_once_with(mcp_config_path=expected_mcp_config)