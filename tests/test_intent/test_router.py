"""
意图路由器单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.intent.router import IntentRouter
from app.services.intent.classifier import IntentType, IntentResult
from app.tools.base import ToolResult


class TestIntentRouter:
    """意图路由器测试"""
    
    @pytest.fixture
    def router(self):
        """创建路由器实例"""
        return IntentRouter()
    
    def test_init(self, router):
        """测试初始化"""
        assert router.classifier is not None
        assert len(router._handlers) > 0
    
    def test_handlers_registered(self, router):
        """测试处理器注册"""
        assert IntentType.WEATHER in router._handlers
        assert IntentType.NEWS in router._handlers
        assert IntentType.SEARCH in router._handlers
        assert IntentType.KNOWLEDGE in router._handlers
        assert IntentType.CHAT in router._handlers
    
    def test_set_history_getter(self, router):
        """测试设置历史获取函数"""
        def mock_getter(session_id):
            return [{"role": "user", "content": "你好"}]
        
        router.set_history_getter(mock_getter)
        assert router._history_getter is not None
        
        history = router._get_history("test_session")
        assert len(history) == 1
    
    def test_get_history_no_getter(self, router):
        """测试无历史获取函数"""
        history = router._get_history("test_session")
        assert history == []
    
    def test_register_custom_handler(self, router):
        """测试注册自定义处理器"""
        async def custom_handler(user_input, intent_result, session_id=None):
            return {"reply": "自定义回复", "tool_result": None, "tool_name": None}
        
        router.register_handler(IntentType.CHAT, custom_handler)
        assert router._handlers[IntentType.CHAT] == custom_handler
    
    @pytest.mark.asyncio
    async def test_route_weather(self, router):
        """测试天气路由"""
        with patch.object(router.classifier, 'classify') as mock_classify:
            mock_classify.return_value = IntentResult(
                intent=IntentType.WEATHER,
                confidence=0.95,
                entities={"city": "北京"},
                raw_text="北京天气",
                source="keyword"
            )
            
            # Mock _handle_tool_with_llm 方法
            async def mock_handler(user_input, intent_result, session_id=None):
                return {
                    "reply": "北京今天晴朗",
                    "tool_result": {"city": "北京", "weather": "晴"},
                    "tool_name": "get_weather"
                }
            
            router._handlers[IntentType.WEATHER] = mock_handler
            
            result = await router.route("北京天气怎么样")
            
            assert result["intent"] == "weather"
            assert result["reply"] == "北京今天晴朗"
            assert result["tool_name"] == "get_weather"
    
    @pytest.mark.asyncio
    async def test_route_chat(self, router):
        """测试闲聊路由"""
        with patch.object(router.classifier, 'classify') as mock_classify:
            mock_classify.return_value = IntentResult(
                intent=IntentType.CHAT,
                confidence=0.9,
                entities={},
                raw_text="你好",
                source="keyword"
            )
            
            # Mock LLM 服务
            mock_llm = AsyncMock()
            mock_llm.chat.return_value = "你好！"
            
            with patch('app.services.intent.router.ServiceFactory') as mock_factory:
                mock_factory.create_llm.return_value = mock_llm
                
                result = await router.route("你好")
                
                assert result["intent"] == "chat"
                assert result["reply"] == "你好！"
    
    @pytest.mark.asyncio
    async def test_route_with_session(self, router):
        """测试带会话的路由"""
        def mock_getter(session_id):
            return [{"role": "user", "content": "之前的消息"}]
        
        router.set_history_getter(mock_getter)
        
        with patch.object(router.classifier, 'classify') as mock_classify:
            mock_classify.return_value = IntentResult(
                intent=IntentType.CHAT,
                confidence=0.9,
                entities={},
                raw_text="那上海呢",
                source="keyword"
            )
            
            # Mock LLM 服务
            mock_llm = AsyncMock()
            mock_llm.chat.return_value = "上海也很好"
            
            with patch('app.services.intent.router.ServiceFactory') as mock_factory:
                mock_factory.create_llm.return_value = mock_llm
                
                result = await router.route("那上海呢", session_id="test_session")
                
                assert result["intent"] == "chat"
                assert result["reply"] == "上海也很好"
    
    def test_build_tool_prompt(self, router):
        """测试工具提示词构建"""
        prompt = router._build_tool_prompt(
            "北京天气", 
            "get_weather", 
            {"city": "北京", "weather": "晴"}
        )
        
        assert "北京天气" in prompt or "天气" in prompt
        assert "北京" in prompt
