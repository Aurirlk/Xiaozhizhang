"""
工具注册表
统一管理所有 Function Calling 工具
"""
from typing import Dict, List, Any, Optional

from app.tools.base import BaseTool, ToolResult
from app.tools.weather_tool import WeatherTool
from app.tools.news_tool import NewsTool
from app.tools.search_tool import SearchTool
from app.tools.knowledge_tool import KnowledgeTool
from app.utils.logger import logger


class ToolRegistry:
    """
    工具注册表
    
    统一管理所有 Function Calling 工具的注册和调用
    """
    
    _instance = None
    _tools: Dict[str, BaseTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._register_default_tools()
        return cls._instance
    
    def _register_default_tools(self):
        """注册默认工具"""
        self.register(WeatherTool())
        self.register(NewsTool())
        self.register(SearchTool())
        self.register(KnowledgeTool())
    
    def register(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool
        logger.info(f"[ToolRegistry] 注册工具: {tool.name}")
    
    def unregister(self, tool_name: str):
        """注销工具"""
        if tool_name in self._tools:
            del self._tools[tool_name]
            logger.info(f"[ToolRegistry] 注销工具: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具实例"""
        return self._tools.get(tool_name)
    
    def get_all_tools(self) -> Dict[str, BaseTool]:
        """获取所有工具"""
        return self._tools.copy()
    
    def get_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的 Schema（供 LLM Function Calling 使用）"""
        return [tool.get_schema_dict() for tool in self._tools.values()]
    
    def get_tool_names(self) -> List[str]:
        """获取所有工具名称"""
        return list(self._tools.keys())
    
    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """
        执行指定工具
        
        Args:
            tool_name: 工具名称
            **kwargs: 工具参数
            
        Returns:
            ToolResult 执行结果
        """
        tool = self._tools.get(tool_name)
        
        if tool is None:
            return ToolResult(
                success=False,
                data=None,
                error=f"工具 '{tool_name}' 不存在",
                tool_name=tool_name
            )
        
        # 验证参数
        if not tool.validate_params(**kwargs):
            return ToolResult(
                success=False,
                data=None,
                error=f"工具 '{tool_name}' 参数无效",
                tool_name=tool_name
            )
        
        # 执行工具
        logger.info(f"[ToolRegistry] 执行工具: {tool_name}, 参数: {kwargs}")
        result = await tool.execute(**kwargs)
        logger.info(f"[ToolRegistry] 工具执行完成: {tool_name}, 成功: {result.success}")
        
        return result


# 全局工具注册表实例
tool_registry = ToolRegistry()
