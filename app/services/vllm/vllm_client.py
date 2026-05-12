"""
VLLM 视觉大模型客户端
支持 Qwen-VL、GPT-4o 等视觉语言模型
"""
import base64
import os
from typing import Optional, Dict, Any, List

import httpx

from app.utils.logger import logger
from app.utils.config_loader import config


class VLLMClient:
    """
    视觉大模型客户端
    
    支持：
    - 图片理解（看图说话）
    - 多模态对话（文本+图片）
    """
    
    def __init__(self, provider: str = "qwen"):
        """
        初始化 VLLM 客户端
        
        Args:
            provider: 模型提供商 (qwen/openai)
        """
        self.provider = provider
        
        # 从配置获取
        vllm_config = config.get("VLLM", provider, default={})
        
        if provider == "qwen":
            self.api_key = vllm_config.get("api_key") or os.getenv("QWEN_API_KEY")
            self.api_url = vllm_config.get("url", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")
            self.model = vllm_config.get("model", "qwen-vl-plus")
        elif provider == "openai":
            self.api_key = vllm_config.get("api_key") or os.getenv("OPENAI_API_KEY")
            self.api_url = vllm_config.get("url", "https://api.openai.com/v1/chat/completions")
            self.model = vllm_config.get("model", "gpt-4o")
        else:
            raise ValueError(f"不支持的 VLLM 提供商: {provider}")
        
        self.timeout = vllm_config.get("timeout", 60)
        
        logger.info(f"[VLLM] 初始化: provider={provider}, model={self.model}")
    
    async def understand_image(
        self, 
        image_path: str, 
        prompt: str = "请描述这张图片的内容"
    ) -> str:
        """
        理解图片内容
        
        Args:
            image_path: 图片路径
            prompt: 提示词
            
        Returns:
            图片描述文本
        """
        # 读取并编码图片
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        # 根据提供商构建请求
        if self.provider == "qwen":
            return await self._qwen_vl_chat(
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
        elif self.provider == "openai":
            return await self._openai_vl_chat(
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
    
    async def multimodal_chat(
        self, 
        text: str, 
        image_path: Optional[str] = None,
        history: Optional[List[Dict]] = None
    ) -> str:
        """
        多模态对话（文本+图片）
        
        Args:
            text: 文本输入
            image_path: 图片路径（可选）
            history: 对话历史
            
        Returns:
            回复文本
        """
        messages = []
        
        # 添加历史
        if history:
            messages.extend(history)
        
        # 构建用户消息
        if image_path:
            # 带图片的消息
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")
            
            messages.append({
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                    {"type": "text", "text": text}
                ]
            })
        else:
            # 纯文本消息
            messages.append({"role": "user", "content": text})
        
        # 调用对应的模型
        if self.provider == "qwen":
            return await self._qwen_vl_chat(messages)
        elif self.provider == "openai":
            return await self._openai_vl_chat(messages)
    
    async def _qwen_vl_chat(self, messages: List[Dict]) -> str:
        """调用 Qwen-VL API"""
        if not self.api_key:
            raise ValueError("QWEN_API_KEY 未配置")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 1024
                    }
                )
            
            if response.status_code != 200:
                raise Exception(f"Qwen-VL API 调用失败: {response.status_code}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"[VLLM] Qwen-VL 调用失败: {e}")
            raise
    
    async def _openai_vl_chat(self, messages: List[Dict]) -> str:
        """调用 OpenAI GPT-4o API"""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 未配置")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 1024
                    }
                )
            
            if response.status_code != 200:
                raise Exception(f"OpenAI API 调用失败: {response.status_code}")
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            logger.error(f"[VLLM] OpenAI 调用失败: {e}")
            raise
    
    async def chat(
        self, 
        messages: List[Dict],
        provider: Optional[str] = None
    ) -> str:
        """
        通用对话接口
        
        Args:
            messages: 消息列表
            provider: 提供商（覆盖默认）
            
        Returns:
            回复文本
        """
        provider = provider or self.provider
        
        if provider == "qwen":
            return await self._qwen_vl_chat(messages)
        elif provider == "openai":
            return await self._openai_vl_chat(messages)
        else:
            raise ValueError(f"不支持的提供商: {provider}")
    
    async def chat_stream(
        self, 
        messages: List[Dict],
        provider: Optional[str] = None
    ):
        """
        流式对话接口
        
        Args:
            messages: 消息列表
            provider: 提供商
            
        Yields:
            回复文本片段
        """
        provider = provider or self.provider
        
        if provider == "qwen":
            async for chunk in self._qwen_vl_chat_stream(messages):
                yield chunk
        elif provider == "openai":
            async for chunk in self._openai_vl_chat_stream(messages):
                yield chunk
    
    async def _qwen_vl_chat_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """Qwen-VL 流式对话"""
        if not self.api_key:
            raise ValueError("QWEN_API_KEY 未配置")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 1024,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data.strip() == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                content = chunk["choices"][0]["delta"].get("content", "")
                                if content:
                                    yield content
                            except:
                                continue
        except Exception as e:
            logger.error(f"[VLLM] Qwen-VL 流式调用失败: {e}")
            raise
    
    async def _openai_vl_chat_stream(self, messages: List[Dict]) -> AsyncGenerator[str, None]:
        """OpenAI GPT-4o 流式对话"""
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 未配置")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                async with client.stream(
                    "POST",
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "max_tokens": 1024,
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data = line[6:]
                            if data.strip() == "[DONE]":
                                break
                            try:
                                import json
                                chunk = json.loads(data)
                                content = chunk["choices"][0]["delta"].get("content", "")
                                if content:
                                    yield content
                            except:
                                continue
        except Exception as e:
            logger.error(f"[VLLM] OpenAI 流式调用失败: {e}")
            raise
