"""
LLM (Large Language Model) 抽象基类
定义大语言模型对话服务的统一接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, AsyncGenerator


class LLMBase(ABC):
    """大语言模型对话服务抽象基类"""
    
    @abstractmethod
    async def chat(
        self, 
        user_message: str, 
        history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        与大模型进行对话
        
        Args:
            user_message: 用户消息
            history: 对话历史 [{"role": "user/assistant", "content": "..."}]
            
        Returns:
            模型回复文本
        """
        pass
    
    @abstractmethod
    async def chat_stream(
        self, 
        user_message: str, 
        history: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        与大模型进行流式对话
        
        Args:
            user_message: 用户消息
            history: 对话历史
            
        Yields:
            模型回复的文本片段
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """
        获取模型名称
        
        Returns:
            模型名称，如 "deepseek-v4-flash"
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        获取服务提供商名称
        
        Returns:
            提供商名称，如 "deepseek", "minimax"
        """
        pass
