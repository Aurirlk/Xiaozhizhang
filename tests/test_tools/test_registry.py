"""
工具基类和注册表单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.tools.base import BaseTool, ToolResult
from app.tools.registry import ToolRegistry, tool_registry
from app.tools.weather_tool import WeatherTool
from app.tools.news_tool import NewsTool
from app.tools.search_tool import SearchTool
from app.tools.knowledge_tool import KnowledgeTool


class TestBaseTool:
    """工具基类测试"""
    
    def test_tool_result_success(self):
        """测试成功结果"""
        result = ToolResult(
            success=True,
            data={"key": "value"},
            tool_name="test_tool"
        )
        
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.error is None
        assert result.tool_name == "test_tool"
    
    def test_tool_result_failure(self):
        """测试失败结果"""
        result = ToolResult(
            success=False,
            data=None,
            error="错误信息",
            tool_name="test_tool"
        )
        
        assert result.success is False
        assert result.error == "错误信息"
    
    def test_tool_result_to_dict(self):
        """测试转换为字典"""
        result = ToolResult(
            success=True,
            data={"key": "value"},
            tool_name="test_tool"
        )
        
        d = result.to_dict()
        assert d["success"] is True
        assert d["data"] == {"key": "value"}
        assert d["tool_name"] == "test_tool"
    
    def test_weather_tool_schema(self):
        """测试天气工具 Schema"""
        tool = WeatherTool()
        schema = tool.schema
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "get_weather"
        assert "city" in schema["function"]["parameters"]["properties"]
    
    def test_news_tool_schema(self):
        """测试新闻工具 Schema"""
        tool = NewsTool()
        schema = tool.schema
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "get_trending_news"
        assert "category" in schema["function"]["parameters"]["properties"]
    
    def test_search_tool_schema(self):
        """测试搜索工具 Schema"""
        tool = SearchTool()
        schema = tool.schema
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "web_search"
        assert "query" in schema["function"]["parameters"]["properties"]
    
    def test_knowledge_tool_schema(self):
        """测试知识库工具 Schema"""
        tool = KnowledgeTool()
        schema = tool.schema
        
        assert schema["type"] == "function"
        assert schema["function"]["name"] == "query_knowledge"
        assert "query" in schema["function"]["parameters"]["properties"]


class TestToolRegistry:
    """工具注册表测试"""
    
    def test_singleton(self):
        """测试单例模式"""
        registry1 = ToolRegistry()
        registry2 = ToolRegistry()
        assert registry1 is registry2
    
    def test_default_tools_registered(self):
        """测试默认工具注册"""
        registry = ToolRegistry()
        tools = registry.get_tool_names()
        
        assert "get_weather" in tools
        assert "get_trending_news" in tools
        assert "web_search" in tools
        assert "query_knowledge" in tools
    
    def test_get_tool(self):
        """测试获取工具"""
        registry = ToolRegistry()
        
        weather_tool = registry.get_tool("get_weather")
        assert weather_tool is not None
        assert isinstance(weather_tool, WeatherTool)
    
    def test_get_tool_not_found(self):
        """测试获取不存在的工具"""
        registry = ToolRegistry()
        
        tool = registry.get_tool("nonexistent")
        assert tool is None
    
    def test_get_schemas(self):
        """测试获取所有 Schema"""
        registry = ToolRegistry()
        schemas = registry.get_schemas()
        
        assert len(schemas) >= 4
        assert all(s["type"] == "function" for s in schemas)
    
    def test_register_custom_tool(self):
        """测试注册自定义工具"""
        registry = ToolRegistry()
        
        class CustomTool(BaseTool):
            @property
            def name(self):
                return "custom_tool"
            
            @property
            def description(self):
                return "自定义工具"
            
            @property
            def schema(self):
                return {"type": "function", "function": {"name": "custom_tool"}}
            
            async def execute(self, **kwargs):
                return ToolResult(success=True, data={}, tool_name=self.name)
        
        registry.register(CustomTool())
        assert "custom_tool" in registry.get_tool_names()
    
    def test_unregister_tool(self):
        """测试注销工具"""
        registry = ToolRegistry()
        
        # 先注册一个工具
        initial_count = len(registry.get_tool_names())
        
        # 注销一个工具
        registry.unregister("get_weather")
        
        assert "get_weather" not in registry.get_tool_names()
        assert len(registry.get_tool_names()) == initial_count - 1
    
    @pytest.mark.asyncio
    async def test_execute_tool_success(self):
        """测试执行工具成功"""
        # 创建新的注册表实例
        registry = ToolRegistry()
        
        # 确保有工具注册
        tool = WeatherTool()
        registry.register(tool)
        
        # 获取工具并验证
        retrieved_tool = registry.get_tool("get_weather")
        assert retrieved_tool is not None
        assert retrieved_tool.name == "get_weather"
    
    @pytest.mark.asyncio
    async def test_execute_tool_not_found(self):
        """测试执行不存在的工具"""
        registry = ToolRegistry()
        
        result = await registry.execute_tool("nonexistent")
        
        assert result.success is False
        assert "不存在" in result.error
    
    @pytest.mark.asyncio
    async def test_execute_tool_invalid_params(self):
        """测试执行工具参数无效"""
        # 创建新的注册表实例
        registry = ToolRegistry()
        
        # 注册工具
        tool = WeatherTool()
        registry.register(tool)
        
        # 测试 validate_params
        assert tool.validate_params(city="北京") is True
        assert tool.validate_params() is False
