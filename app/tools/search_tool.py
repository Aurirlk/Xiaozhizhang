"""
网页搜索工具
基于 Bing 搜索的 Function Calling 工具
"""
import json
from typing import Any, Dict

from app.tools.base import BaseTool, ToolResult
from app.utils.logger import logger


class SearchTool(BaseTool):
    """网页搜索工具"""
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "执行互联网搜索引擎查询。当用户询问你不懂的最新知识、实时新闻、或者要求你'上网查一下'时调用此工具。"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "搜索关键词，例如：'2026年世界杯举办地' 或 '今天A股大盘走势'"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "返回的最大结果数量，默认3条",
                            "default": 3
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行网页搜索"""
        query = kwargs.get("query", "")
        max_results = kwargs.get("max_results", 3)
        
        if not query:
            return ToolResult(
                success=False,
                data=None,
                error="搜索关键词不能为空",
                tool_name=self.name
            )
        
        try:
            from app.plugins.web_search import execute_web_search
            
            result_str = await execute_web_search(query, max_results)
            result_data = json.loads(result_str)
            
            if "error" in result_data:
                return ToolResult(
                    success=False,
                    data=None,
                    error=result_data["error"],
                    tool_name=self.name
                )
            
            return ToolResult(
                success=True,
                data=result_data,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"[SearchTool] 执行失败: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool_name=self.name
            )
