import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class ToolRegistry:
    """
    静的設定(JSON)の読み込みと、複数MCPサーバーからのツールマージ・競合解決を行う
    """
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_json(config_path)
        # 最終的にAIに提示し、ルーティングに使用するツールの辞書
        self.active_tools: Dict[str, Dict[str, Any]] = {}

    def _load_json(self, path: str) -> Dict[str, Any]:
        """JSONファイルを読み込む。"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load config from {path}: {e}")
            return {}

    def merge_and_resolve_tools(self, backend_tools_map: Dict[str, List[Dict[str, Any]]]):
        """
        各バックエンドから取得したツールリストを結合し、設定に基づいて競合解決・フィルタリングを行う。
        (起動時に一度だけ呼び出される想定)
        """
        resolved_tools = {}

        # 1. プレフィックス付き登録 ＆ 暗黙のベース名（後勝ち）登録
        for server_name in sorted(backend_tools_map.keys()):
            for raw_tool in backend_tools_map[server_name]:
                base_tool_name = raw_tool["name"]
                
                # A. プレフィックス付きツール
                namespaced_name = f"{server_name}_{base_tool_name}"
                namespaced_tool = raw_tool.copy()
                namespaced_tool["name"] = namespaced_name
                namespaced_tool["_target_server"] = server_name
                namespaced_tool["_backend_tool_name"] = base_tool_name
                resolved_tools[namespaced_name] = namespaced_tool
                
                # B. ベース名での登録
                resolved_tools[base_tool_name] = self._create_proxy_tool(base_tool_name, server_name, raw_tool)

        # 2. explicit_routing (明示的なオーバーライド) の適用 [優先度: 高]
        explicit_routing = self.config.get("explicit_routing", {})
        for base_tool_name, target_server in explicit_routing.items():
            target_raw_tool = self._get_raw_tool(backend_tools_map, target_server, base_tool_name)
            if target_raw_tool:
                resolved_tools[base_tool_name] = self._create_proxy_tool(base_tool_name, target_server, target_raw_tool)
                logger.info(f"Explicitly routed '{base_tool_name}' to {target_server}")
            else:
                logger.warning(f"Explicit routing failed: Server '{target_server}' does not have tool '{base_tool_name}'")

        # 3. 仮想ツール(Facade) への置き換え [優先度: 最高]
        self.active_tools = self._apply_virtual_tool_replacements(resolved_tools)
        
        # 4. ブロックツールの削除
        self._apply_blocked_tools()

    def _create_proxy_tool(self, tool_name: str, target_server: str, raw_tool: Dict[str, Any]) -> Dict[str, Any]:
        proxy_tool = raw_tool.copy()
        proxy_tool["name"] = tool_name
        proxy_tool["_target_server"] = target_server
        proxy_tool["_backend_tool_name"] = raw_tool["name"]
        return proxy_tool

    def _get_raw_tool(self, backend_tools_map: Dict[str, List[Dict[str, Any]]], server_name: str, tool_name: str) -> Optional[Dict[str, Any]]:
        tools = backend_tools_map.get(server_name, [])
        for tool in tools:
            if tool["name"] == tool_name:
                return tool
        return None

    def _apply_virtual_tool_replacements(self, resolved_tools: Dict[str, Any]) -> Dict[str, Any]:
        virtual_tools_config = self.config.get("virtual_tools", {})
        final_tools = resolved_tools.copy()

        for v_name, v_config in virtual_tools_config.items():
            virtual_tool = {
                "name": v_name,
                "description": v_config.get("description", ""),
                "inputSchema": v_config.get("inputSchema", {"type": "object", "properties": {}}),
                "_target_server": v_config.get("target_server")
            }
            final_tools[v_name] = virtual_tool
            logger.info(f"Registered virtual tool: {v_name}")

        return final_tools

    def _apply_blocked_tools(self):
        blocked_tools = self.config.get("blocked_tools", [])
        for tool_name in blocked_tools:
            if tool_name in self.active_tools:
                del self.active_tools[tool_name]
                logger.info(f"Blocked tool removed: {tool_name}")

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        llm_tools = []
        for tool in self.active_tools.values():
            clean_tool = tool.copy()
            clean_tool = {k: v for k, v in clean_tool.items() if not k.startswith("_")}
            llm_tools.append(clean_tool)
        return llm_tools

    def get_tool_routing_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        tool = self.active_tools.get(tool_name)
        if not tool:
            return None
        return {
            "target_server": tool.get("_target_server"),
            "backend_tool_name": tool.get("_backend_tool_name", tool_name)
        }