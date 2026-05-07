"""
服务工厂单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.factory import ServiceFactory, ServiceProvider, FallbackLLM, FallbackTTS
from app.services.llm.deepseek_llm import DeepSeekLLM
from app.services.llm.minimax_llm import MiniMaxLLM
from app.services.tts.mimo_tts import MiMoTTS
from app.services.tts.minimax_tts import MiniMaxTTS
from app.services.asr.minimax_asr import MiniMaxASR


class TestServiceFactory:
    """服务工厂测试"""
    
    def test_create_llm_deepseek(self):
        """测试创建 DeepSeek LLM"""
        with patch('app.services.factory.settings') as mock_settings:
            mock_settings.DEEPSEEK_API_KEY = "test_key"
            llm = ServiceFactory.create_llm("deepseek")
            assert isinstance(llm, DeepSeekLLM)
    
    def test_create_llm_minimax(self):
        """测试创建 MiniMax LLM"""
        with patch('app.services.factory.settings') as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test_key"
            llm = ServiceFactory.create_llm("minimax")
            assert isinstance(llm, MiniMaxLLM)
    
    def test_create_llm_auto_deepseek(self):
        """测试自动选择 LLM（优先 DeepSeek）"""
        with patch('app.services.factory.settings') as mock_settings:
            mock_settings.DEEPSEEK_API_KEY = "test_key"
            mock_settings.MINIMAX_API_KEY = "test_key"
            llm = ServiceFactory.create_llm("auto")
            assert isinstance(llm, DeepSeekLLM)
    
    def test_create_llm_auto_fallback(self):
        """测试自动选择 LLM（回退到 MiniMax）"""
        with patch('app.services.factory.settings') as mock_settings:
            mock_settings.DEEPSEEK_API_KEY = None
            mock_settings.MINIMAX_API_KEY = "test_key"
            llm = ServiceFactory.create_llm("auto")
            assert isinstance(llm, MiniMaxLLM)
    
    def test_create_llm_no_key(self):
        """测试无 API Key 时抛出异常"""
        with patch('app.services.factory.settings') as mock_settings:
            mock_settings.DEEPSEEK_API_KEY = None
            mock_settings.MINIMAX_API_KEY = None
            
            with pytest.raises(ValueError, match="未配置任何 LLM API Key"):
                ServiceFactory.create_llm("auto")
    
    def test_create_llm_invalid_provider(self):
        """测试无效提供商"""
        with pytest.raises(ValueError, match="不支持的 LLM 提供商"):
            ServiceFactory.create_llm("invalid")
    
    def test_create_tts_mimo(self):
        """测试创建 MiMo TTS"""
        with patch('app.services.factory.settings') as mock_settings:
            mock_settings.MIMO_TTS_API_KEY = "test_key"
            tts = ServiceFactory.create_tts("mimo")
            assert isinstance(tts, MiMoTTS)
    
    def test_create_tts_minimax(self):
        """测试创建 MiniMax TTS"""
        with patch('app.services.factory.settings') as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test_key"
            tts = ServiceFactory.create_tts("minimax")
            assert isinstance(tts, MiniMaxTTS)
    
    def test_create_asr_minimax(self):
        """测试创建 MiniMax ASR"""
        with patch('app.services.factory.settings') as mock_settings:
            mock_settings.MINIMAX_API_KEY = "test_key"
            asr = ServiceFactory.create_asr("minimax")
            assert isinstance(asr, MiniMaxASR)
    
    def test_create_asr_invalid_provider(self):
        """测试无效 ASR 提供商"""
        with pytest.raises(ValueError, match="不支持的 ASR 提供商"):
            ServiceFactory.create_asr("invalid")


class TestServiceProvider:
    """服务提供商枚举测试"""
    
    def test_provider_values(self):
        """测试枚举值"""
        assert ServiceProvider.AUTO.value == "auto"
        assert ServiceProvider.DEEPSEEK.value == "deepseek"
        assert ServiceProvider.MINIMAX.value == "minimax"
        assert ServiceProvider.MIMO.value == "mimo"
        assert ServiceProvider.WHISPER.value == "whisper"


class TestFallbackLLM:
    """回退 LLM 测试"""
    
    @pytest.mark.asyncio
    async def test_fallback_success(self):
        """测试主服务成功"""
        with patch('app.services.factory.ServiceFactory.create_llm') as mock_create:
            mock_llm = AsyncMock()
            mock_llm.chat.return_value = "回复"
            mock_create.return_value = mock_llm
            
            fallback = FallbackLLM(providers=["deepseek"])
            result = await fallback.chat("你好")
            assert result == "回复"
    
    def test_get_provider_name(self):
        """测试获取提供商名称"""
        with patch('app.services.factory.ServiceFactory.create_llm') as mock_create:
            mock_llm = MagicMock()
            mock_llm.get_provider_name.return_value = "deepseek"
            mock_create.return_value = mock_llm
            
            fallback = FallbackLLM(providers=["deepseek"])
            assert "deepseek" in fallback.get_provider_name()


class TestFallbackTTS:
    """回退 TTS 测试"""
    
    @pytest.mark.asyncio
    async def test_fallback_success(self):
        """测试主服务成功"""
        with patch('app.services.factory.ServiceFactory.create_tts') as mock_create:
            mock_tts = AsyncMock()
            mock_tts.synthesize.return_value = "outputs/test.wav"
            mock_create.return_value = mock_tts
            
            fallback = FallbackTTS(providers=["mimo"])
            result = await fallback.synthesize("你好")
            assert result == "outputs/test.wav"
