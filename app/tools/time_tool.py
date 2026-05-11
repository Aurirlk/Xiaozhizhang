"""
时间查询工具
通过 Python 硬编码获取当前时间信息
"""
from datetime import datetime
import pytz
from typing import Any, Dict

from app.tools.base import BaseTool, ToolResult
from app.utils.logger import logger


class TimeTool(BaseTool):
    """时间查询工具"""
    
    @property
    def name(self) -> str:
        return "get_time"
    
    @property
    def description(self) -> str:
        return "获取当前时间信息。当用户询问时间、日期、今天几号、现在几点等问题时调用此工具。"
    
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
                        "timezone": {
                            "type": "string",
                            "description": "时区名称，例如：'Asia/Shanghai'、'America/New_York'。默认为中国时区。",
                            "default": "Asia/Shanghai"
                        },
                        "format": {
                            "type": "string",
                            "description": "返回格式：'full'(完整日期时间)、'date'(仅日期)、'time'(仅时间)、'weekday'(星期几)",
                            "enum": ["full", "date", "time", "weekday"],
                            "default": "full"
                        }
                    }
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行时间查询"""
        try:
            timezone_str = kwargs.get("timezone", "Asia/Shanghai")
            format_type = kwargs.get("format", "full")
            
            # 获取时区
            try:
                tz = pytz.timezone(timezone_str)
            except pytz.exceptions.UnknownTimeZoneError:
                tz = pytz.timezone("Asia/Shanghai")
                timezone_str = "Asia/Shanghai"
            
            # 获取当前时间
            now = datetime.now(tz)
            
            # 构建返回结果
            result = {
                "timezone": timezone_str,
                "timestamp": now.isoformat(),
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "second": now.second,
                "weekday": self._get_weekday_cn(now.weekday()),
                "date": now.strftime("%Y年%m月%d日"),
                "time": now.strftime("%H:%M:%S"),
                "datetime": now.strftime("%Y年%m月%d日 %H:%M:%S")
            }
            
            # 根据格式返回
            if format_type == "date":
                result["formatted"] = now.strftime("%Y年%m月%d日")
            elif format_type == "time":
                result["formatted"] = now.strftime("%H:%M:%S")
            elif format_type == "weekday":
                result["formatted"] = f"今天是{self._get_weekday_cn(now.weekday())}"
            else:
                result["formatted"] = now.strftime("%Y年%m月%d日 %H:%M:%S")
            
            logger.info(f"[TimeTool] 查询时间: {result['formatted']}")
            
            return ToolResult(
                success=True,
                data=result,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"[TimeTool] 执行失败: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool_name=self.name
            )
    
    def _get_weekday_cn(self, weekday: int) -> str:
        """获取中文星期"""
        weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        return weekdays[weekday]
