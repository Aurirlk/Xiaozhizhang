"""
天气查询工具
基于和风天气 API 的 Function Calling 工具
"""
import os
import json
from typing import Any, Dict

from app.tools.base import BaseTool, ToolResult
from app.utils.logger import logger


class WeatherTool(BaseTool):
    """天气查询工具"""
    
    @property
    def name(self) -> str:
        return "get_weather"
    
    @property
    def description(self) -> str:
        return "获取指定中国城市的实时天气信息。当用户询问任何关于天气、气温、下雨等问题时，必须调用此工具。"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "需要查询的城市名称，例如：北京、广州、深圳。不要带'市'字。"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行天气查询"""
        city = kwargs.get("city", "北京")
        
        try:
            from app.plugins.get_weather import execute_get_weather
            
            result_str = await execute_get_weather(city)
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
            logger.error(f"[WeatherTool] 执行失败: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool_name=self.name
            )
    
    @property
    def schema(self) -> Dict[str, Any]:
        """Function Calling Schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "需要查询的城市名称，例如：北京、广州、深圳。不要带'市'字。"
                        }
                    },
                    "required": ["city"]
                }
            }
        }
