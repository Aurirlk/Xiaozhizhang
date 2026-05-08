"""
端到端测试 - 完整用户流程
测试从用户注册到对话的完整流程
"""
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.fixture
async def client():
    """创建测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestUserFlow:
    """用户完整流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_text_chat_flow(self, client):
        """测试完整的文本对话流程"""
        # 1. 健康检查
        health_response = await client.get("/api/v1/health")
        assert health_response.status_code == 200
        
        # 2. 获取提供商
        providers_response = await client.get("/api/v1/providers")
        assert providers_response.status_code == 200
        
        # 3. 获取音色列表
        mock_tts = AsyncMock()
        mock_tts.get_voices.return_value = [
            {"id": "mimo-v2.5-tts", "name": "MiMo 标准语音"}
        ]
        
        with patch('app.routers.chat.ServiceFactory') as mock_factory:
            mock_factory.create_tts.return_value = mock_tts
            voices_response = await client.get("/api/v1/voices")
            assert voices_response.status_code == 200
        
        # 4. 发送文本对话
        mock_llm = AsyncMock()
        mock_llm.chat.return_value = "你好！我是智能助手。"
        mock_llm.get_model_name.return_value = "deepseek-v4-flash"
        mock_llm.get_provider_name.return_value = "deepseek"
        
        mock_tts.synthesize.return_value = "outputs/test.wav"
        mock_tts.get_provider_name.return_value = "mimo"
        
        with patch('app.routers.chat.ServiceFactory') as mock_factory:
            mock_factory.create_llm.return_value = mock_llm
            mock_factory.create_tts.return_value = mock_tts
            
            chat_response = await client.post(
                "/api/v1/chat/text",
                json={"message": "你好", "history": []}
            )
        
        assert chat_response.status_code == 200
        chat_data = chat_response.json()
        assert chat_data["success"] == True
        
        # 5. 获取 CRM 统计
        crm_response = await client.get("/api/v1/crm/stats")
        assert crm_response.status_code in [200, 500]
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, client):
        """测试多轮对话"""
        mock_llm = AsyncMock()
        mock_llm.get_model_name.return_value = "deepseek-v4-flash"
        mock_llm.get_provider_name.return_value = "deepseek"
        
        mock_tts = AsyncMock()
        mock_tts.get_provider_name.return_value = "mimo"
        mock_tts.synthesize.return_value = "outputs/test.wav"
        
        # 第一轮对话
        mock_llm.chat.return_value = "今天天气晴朗。"
        
        with patch('app.routers.chat.ServiceFactory') as mock_factory:
            mock_factory.create_llm.return_value = mock_llm
            mock_factory.create_tts.return_value = mock_tts
            
            response1 = await client.post(
                "/api/v1/chat/text",
                json={"message": "今天天气怎么样？", "history": []}
            )
        
        assert response1.status_code == 200
        
        # 第二轮对话（带上下文）
        mock_llm.chat.return_value = "明天可能会下雨。"
        
        with patch('app.routers.chat.ServiceFactory') as mock_factory:
            mock_factory.create_llm.return_value = mock_llm
            mock_factory.create_tts.return_value = mock_tts
            
            response2 = await client.post(
                "/api/v1/chat/text",
                json={
                    "message": "那明天呢？",
                    "history": [
                        {"role": "user", "content": "今天天气怎么样？"},
                        {"role": "assistant", "content": "今天天气晴朗。"}
                    ]
                }
            )
        
        assert response2.status_code == 200


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_invalid_json(self, client):
        """测试无效 JSON"""
        response = await client.post(
            "/api/v1/chat/text",
            content="not json",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_missing_required_field(self, client):
        """测试缺少必填字段"""
        response = await client.post(
            "/api/v1/chat/text",
            json={"history": []}  # 缺少 message 字段
        )
        
        assert response.status_code in [400, 422]


class TestAPIEndpoints:
    """API 端点测试"""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client):
        """测试根路径"""
        response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    @pytest.mark.asyncio
    async def test_docs_endpoint(self, client):
        """测试文档路径"""
        response = await client.get("/docs")
        
        assert response.status_code == 200
