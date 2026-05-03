"""
服务工厂模块
统一创建和管理 ASR、LLM、TTS 服务实例
支持单例缓存、自动回退
"""
from enum import Enum
from typing import Optional, Dict, List
import threading

from app.config import settings
from app.services.base.asr_base import ASRBase
from app.services.base.llm_base import LLMBase
from app.services.base.tts_base import TTSBase
from app.utils.logger import logger


class ServiceProvider(str, Enum):
    """服务提供商枚举"""
    AUTO = "auto"
    DEEPSEEK = "deepseek"
    MINIMAX = "minimax"
    MIMO = "mimo"
    WHISPER = "whisper"


class ServiceFactory:
    """
    服务工厂 - 统一创建和管理服务实例
    
    支持：
    - 单例缓存（避免重复创建）
    - 自动回退（Fallback）
    - 运行时切换模型
    """
    
    # 单例缓存
    _cache: Dict[str, object] = {}
    _lock = threading.Lock()
    
    @classmethod
    def _get_or_create(cls, key: str, creator_func):
        """获取缓存的实例或创建新实例"""
        if key not in cls._cache:
            with cls._lock:
                if key not in cls._cache:
                    cls._cache[key] = creator_func()
        return cls._cache[key]
    
    @classmethod
    def clear_cache(cls):
        """清空缓存"""
        with cls._lock:
            cls._cache.clear()
    
    @staticmethod
    def create_asr(provider: str = ServiceProvider.AUTO, use_cache: bool = True) -> ASRBase:
        """创建 ASR 服务实例"""
        def _create():
            if provider == ServiceProvider.AUTO:
                return ServiceFactory._create_asr_auto()
            if provider == ServiceProvider.MINIMAX:
                from app.services.asr.minimax_asr import MiniMaxASR
                return MiniMaxASR()
            raise ValueError(f"不支持的 ASR 提供商: {provider}")
        
        if use_cache:
            return ServiceFactory._get_or_create(f"asr_{provider}", _create)
        return _create()
    
    @staticmethod
    def _create_asr_auto() -> ASRBase:
        from app.services.asr.minimax_asr import MiniMaxASR
        if settings.MINIMAX_API_KEY:
            return MiniMaxASR()
        raise ValueError("未配置任何 ASR API Key")
    
    @staticmethod
    def create_llm(provider: str = ServiceProvider.AUTO, use_cache: bool = True) -> LLMBase:
        """创建 LLM 服务实例"""
        def _create():
            if provider == ServiceProvider.AUTO:
                return ServiceFactory._create_llm_auto()
            if provider == ServiceProvider.DEEPSEEK:
                from app.services.llm.deepseek_llm import DeepSeekLLM
                return DeepSeekLLM()
            if provider == ServiceProvider.MINIMAX:
                from app.services.llm.minimax_llm import MiniMaxLLM
                return MiniMaxLLM()
            raise ValueError(f"不支持的 LLM 提供商: {provider}")
        
        if use_cache:
            return ServiceFactory._get_or_create(f"llm_{provider}", _create)
        return _create()
    
    @staticmethod
    def _create_llm_auto() -> LLMBase:
        from app.services.llm.deepseek_llm import DeepSeekLLM
        from app.services.llm.minimax_llm import MiniMaxLLM
        if settings.DEEPSEEK_API_KEY:
            return DeepSeekLLM()
        if settings.MINIMAX_API_KEY:
            return MiniMaxLLM()
        raise ValueError("未配置任何 LLM API Key")
    
    @staticmethod
    def create_tts(provider: str = ServiceProvider.AUTO, use_cache: bool = True) -> TTSBase:
        """创建 TTS 服务实例"""
        def _create():
            if provider == ServiceProvider.AUTO:
                return ServiceFactory._create_tts_auto()
            if provider == ServiceProvider.MIMO:
                from app.services.tts.mimo_tts import MiMoTTS
                return MiMoTTS()
            if provider == ServiceProvider.MINIMAX:
                from app.services.tts.minimax_tts import MiniMaxTTS
                return MiniMaxTTS()
            raise ValueError(f"不支持的 TTS 提供商: {provider}")
        
        if use_cache:
            return ServiceFactory._get_or_create(f"tts_{provider}", _create)
        return _create()
    
    @staticmethod
    def _create_tts_auto() -> TTSBase:
        from app.services.tts.mimo_tts import MiMoTTS
        from app.services.tts.minimax_tts import MiniMaxTTS
        if settings.MIMO_TTS_API_KEY:
            return MiMoTTS()
        if settings.MINIMAX_API_KEY:
            return MiniMaxTTS()
        raise ValueError("未配置任何 TTS API Key")
    
    # ========== Fallback 工厂方法 ==========
    
    @staticmethod
    def create_llm_with_fallback() -> "FallbackLLM":
        """创建带自动回退的 LLM 服务"""
        return FallbackLLM()
    
    @staticmethod
    def create_tts_with_fallback() -> "FallbackTTS":
        """创建带自动回退的 TTS 服务"""
        return FallbackTTS()
    
    @staticmethod
    def create_asr_with_fallback() -> "FallbackASR":
        """创建带自动回退的 ASR 服务"""
        return FallbackASR()


class FallbackASR(ASRBase):
    """带自动回退的 ASR 服务"""
    
    def __init__(self, providers: Optional[list] = None):
        self.providers = providers or [ServiceProvider.MINIMAX]
        self._primary = None
        self._fallback = None
        
        for provider in self.providers:
            try:
                if self._primary is None:
                    self._primary = ServiceFactory.create_asr(provider, use_cache=False)
                else:
                    self._fallback = ServiceFactory.create_asr(provider, use_cache=False)
                    break
            except Exception:
                continue
    
    async def transcribe(self, audio_file_path: str) -> str:
        if self._primary:
            try:
                return await self._primary.transcribe(audio_file_path)
            except Exception as e:
                logger.warning(f"[FallbackASR] 主服务失败: {e}")
                if self._fallback:
                    return await self._fallback.transcribe(audio_file_path)
                raise
        raise ValueError("无可用的 ASR 服务")
    
    def get_supported_formats(self) -> List[str]:
        if self._primary:
            return self._primary.get_supported_formats()
        return []
    
    def get_provider_name(self) -> str:
        return f"fallback({self._primary.get_provider_name() if self._primary else 'none'})"


class FallbackLLM(LLMBase):
    """带自动回退的 LLM 服务"""
    
    def __init__(self, providers: Optional[list] = None):
        self.providers = providers or [ServiceProvider.DEEPSEEK, ServiceProvider.MINIMAX]
        self._primary = None
        self._fallback = None
        
        for provider in self.providers:
            try:
                if self._primary is None:
                    self._primary = ServiceFactory.create_llm(provider, use_cache=False)
                else:
                    self._fallback = ServiceFactory.create_llm(provider, use_cache=False)
                    break
            except Exception:
                continue
    
    async def chat(self, user_message: str, history: Optional[list] = None) -> str:
        if self._primary:
            try:
                return await self._primary.chat(user_message, history)
            except Exception as e:
                logger.warning(f"[FallbackLLM] 主服务失败: {e}")
                if self._fallback:
                    return await self._fallback.chat(user_message, history)
                raise
        raise ValueError("无可用的 LLM 服务")
    
    async def chat_stream(self, user_message: str, history: Optional[list] = None):
        if self._primary:
            try:
                async for chunk in self._primary.chat_stream(user_message, history):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"[FallbackLLM] 主服务流式失败: {e}")
                if self._fallback:
                    async for chunk in self._fallback.chat_stream(user_message, history):
                        yield chunk
                    return
                raise
        raise ValueError("无可用的 LLM 服务")
    
    def get_model_name(self) -> str:
        return self._primary.get_model_name() if self._primary else "none"
    
    def get_provider_name(self) -> str:
        return f"fallback({self._primary.get_provider_name() if self._primary else 'none'})"


class FallbackTTS(TTSBase):
    """带自动回退的 TTS 服务"""
    
    def __init__(self, providers: Optional[list] = None):
        self.providers = providers or [ServiceProvider.MIMO, ServiceProvider.MINIMAX]
        self._primary = None
        self._fallback = None
        
        for provider in self.providers:
            try:
                if self._primary is None:
                    self._primary = ServiceFactory.create_tts(provider, use_cache=False)
                else:
                    self._fallback = ServiceFactory.create_tts(provider, use_cache=False)
                    break
            except Exception:
                continue
    
    async def synthesize(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None) -> str:
        if self._primary:
            try:
                return await self._primary.synthesize(text, voice, speed)
            except Exception as e:
                logger.warning(f"[FallbackTTS] 主服务失败: {e}")
                if self._fallback:
                    return await self._fallback.synthesize(text, voice, speed)
                raise
        raise ValueError("无可用的 TTS 服务")
    
    async def synthesize_stream(self, text: str, voice: Optional[str] = None, speed: Optional[float] = None):
        if self._primary:
            try:
                async for chunk in self._primary.synthesize_stream(text, voice, speed):
                    yield chunk
                return
            except Exception as e:
                logger.warning(f"[FallbackTTS] 主服务流式失败: {e}")
                if self._fallback:
                    async for chunk in self._fallback.synthesize_stream(text, voice, speed):
                        yield chunk
                    return
                raise
        raise ValueError("无可用的 TTS 服务")
    
    async def get_voices(self) -> list:
        if self._primary:
            return await self._primary.get_voices()
        return []
    
    def get_provider_name(self) -> str:
        return f"fallback({self._primary.get_provider_name() if self._primary else 'none'})"
