"""
MCP (Model Context Protocol) 处理器
支持 MCP 协议的工具调用和资源管理
"""
import json
import os
from typing import Any, Dict, List, Optional, Callable

from app.utils.logger import logger
from app.utils.config_loader import config


class MCPHandler:
    """
    MCP 协议处理器
    
    支持：
    - 工具调用 (tools/call)
    - 资源列表 (resources/list)
    - 资源读取 (resources/read)
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools: Dict[str, Callable] = {}
            cls._instance._resources: Dict[str, Any] = {}
        return cls._instance
    
    def __init__(self):
        mcp_config = config.get("MCP", default={})
        self.enabled = mcp_config.get("enabled", True)
        
        # 注册默认工具
        self._register_default_tools()
        
        logger.info(f"[MCP] 初始化完成: enabled={self.enabled}")
    
    def _register_default_tools(self):
        """注册默认 MCP 工具"""
        # 这些工具可以从 NeuVox 的插件系统中调用
        pass
    
    def register_tool(self, name: str, handler: Callable, description: str = ""):
        """
        注册 MCP 工具
        
        Args:
            name: 工具名称
            handler: 处理函数
            description: 工具描述
        """
        self._tools[name] = {
            "handler": handler,
            "description": description
        }
        logger.info(f"[MCP] 注册工具: {name}")
    
    def unregister_tool(self, name: str):
        """注销工具"""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"[MCP] 注销工具: {name}")
    
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理 MCP 请求
        
        Args:
            request: MCP 请求
            
        Returns:
            MCP 响应
        """
        if not self.enabled:
            return {"error": "MCP 未启用"}
        
        method = request.get("method")
        params = request.get("params", {})
        
        try:
            if method == "tools/list":
                return await self._handle_tools_list()
            elif method == "tools/call":
                return await self._handle_tools_call(params)
            elif method == "resources/list":
                return await self._handle_resources_list()
            elif method == "resources/read":
                return await self._handle_resources_read(params)
            else:
                return {"error": f"未知的方法: {method}"}
                
        except Exception as e:
            logger.error(f"[MCP] 请求处理失败: {e}")
            return {"error": str(e)}
    
    async def _handle_tools_list(self) -> Dict[str, Any]:
        """处理工具列表请求"""
        tools = []
        for name, tool_info in self._tools.items():
            tools.append({
                "name": name,
                "description": tool_info.get("description", "")
            })
        
        return {"tools": tools}
    
    async def _handle_tools_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理工具调用请求"""
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        
        if tool_name not in self._tools:
            return {"error": f"工具不存在: {tool_name}"}
        
        try:
            handler = self._tools[tool_name]["handler"]
            result = await handler(**arguments)
            return {"content": [{"type": "text", "text": str(result)}]}
        except Exception as e:
            return {"error": str(e)}
    
    async def _handle_resources_list(self) -> Dict[str, Any]:
        """处理资源列表请求"""
        resources = []
        for name, resource_info in self._resources.items():
            resources.append({
                "uri": f"resource://{name}",
                "name": name,
                "description": resource_info.get("description", "")
            })
        
        return {"resources": resources}
    
    async def _handle_resources_read(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理资源读取请求"""
        uri = params.get("uri", "")
        name = uri.replace("resource://", "")
        
        if name not in self._resources:
            return {"error": f"资源不存在: {name}"}
        
        resource = self._resources[name]
        return {"contents": [{"uri": uri, "text": json.dumps(resource.get("data", {}))}]}
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """获取所有工具的 Schema"""
        schemas = []
        for name, tool_info in self._tools.items():
            schemas.append({
                "name": name,
                "description": tool_info.get("description", "")
            })
        return schemas


# 全局 MCP 处理器实例
mcp_handler = MCPHandler()
