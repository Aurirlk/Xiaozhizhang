"""
TTS (Text-to-Speech) 抽象基类
定义语音合成服务的统一接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncGenerator


class TTSBase(ABC):
    """语音合成服务抽象基类"""
    
    @abstractmethod
    async def synthesize(
        self, 
        text: str, 
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ) -> str:
        """
        将文本转换为语音
        
        Args:
            text: 要转换的文本
            voice: 音色选择（可选）
            speed: 语速控制（可选）
            
        Returns:
            生成的音频文件路径
        """
        pass
    
    @abstractmethod
    async def synthesize_stream(
        self, 
        text: str, 
        voice: Optional[str] = None,
        speed: Optional[float] = None
    ) -> AsyncGenerator[bytes, None]:
        """
        流式语音合成
        
        Args:
            text: 要转换的文本
            voice: 音色选择（可选）
            speed: 语速控制（可选）
            
        Yields:
            音频数据块 (bytes)
        """
        pass
    
    @abstractmethod
    async def get_voices(self) -> List[Dict[str, str]]:
        """
        获取可用音色列表
        
        Returns:
            音色列表 [{"id": "...", "name": "..."}]
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        获取服务提供商名称
        
        Returns:
            提供商名称，如 "mimo", "minimax"
        """
        pass
