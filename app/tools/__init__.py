"""
工具模块
基于 Function Calling 的工具链
"""
from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry, tool_registry
from app.tools.weather_tool import WeatherTool
from app.tools.news_tool import NewsTool
from app.tools.search_tool import SearchTool
from app.tools.knowledge_tool import KnowledgeTool

__all__ = [
    "BaseTool", "ToolResult", "ToolRegistry", "tool_registry",
    "WeatherTool", "NewsTool", "SearchTool", "KnowledgeTool"
]
