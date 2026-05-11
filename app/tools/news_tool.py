"""
新闻获取工具
基于 RSS 新闻源的 Function Calling 工具
"""
import json
from typing import Any, Dict, List

from app.tools.base import BaseTool, ToolResult
from app.utils.logger import logger


class NewsTool(BaseTool):
    """新闻获取工具"""
    
    @property
    def name(self) -> str:
        return "get_trending_news"
    
    @property
    def description(self) -> str:
        return "获取不同分类的最新热点新闻。当用户让你'播报一下新闻'、'有什么大瓜'、'最近军事有什么动向'时调用此工具。"
    
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
                        "category": {
                            "type": "string",
                            "description": "新闻类别。可选值：'society'(社会日常), 'finance'(财经金融), 'world'(国际大事), 'military'(军事动态), 'entertainment'(娱乐八卦), 'sports'(体育赛事)。如果用户没明确要求，默认传 'society'。",
                            "enum": ["society", "finance", "world", "military", "entertainment", "sports"],
                            "default": "society"
                        }
                    }
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行新闻获取"""
        category = kwargs.get("category", "society")
        
        try:
            from app.plugins.get_trending_news import execute_get_trending_news
            
            result_str = await execute_get_trending_news(category)
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
            logger.error(f"[NewsTool] 执行失败: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool_name=self.name
            )
