"""
工具基类
定义 Function Calling 工具的统一接口
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any
    error: Optional[str] = None
    tool_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "tool_name": self.tool_name
        }


class BaseTool(ABC):
    """
    工具基类
    
    所有 Function Calling 工具必须继承此类并实现：
    - name: 工具名称
    - description: 工具描述
    - schema: Function Calling Schema
    - execute(): 执行逻辑
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """工具名称"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """工具描述"""
        pass
    
    @property
    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """
        Function Calling Schema
        
        格式示例：
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "获取天气信息",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名"}
                    },
                    "required": ["city"]
                }
            }
        }
        """
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        执行工具逻辑
        
        Args:
            **kwargs: 工具参数
            
        Returns:
            ToolResult 执行结果
        """
        pass
    
    def get_schema_dict(self) -> Dict[str, Any]:
        """获取 Schema 字典（供 LLM Function Calling 使用）"""
        return self.schema
    
    def validate_params(self, **kwargs) -> bool:
        """
        验证参数是否符合 Schema 要求
        
        Returns:
            是否有效
        """
        schema = self.schema.get("function", {}).get("parameters", {})
        required = schema.get("required", [])
        
        for param in required:
            if param not in kwargs:
                return False
        
        return True
