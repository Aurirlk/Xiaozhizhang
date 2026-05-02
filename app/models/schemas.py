"""
Pydantic 数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class MessageRole(str, Enum):
    """消息角色"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatMessage(BaseModel):
    """对话消息"""
    role: MessageRole
    content: str


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str = Field(..., min_length=1, max_length=2000, description="用户消息")
    history: Optional[List[ChatMessage]] = Field(default=[], description="对话历史")


class ChatResponse(BaseModel):
    """聊天响应"""
    success: bool = Field(default=True, description="是否成功")
    message: str = Field(..., description="回复内容")
    audio_path: Optional[str] = Field(default=None, description="音频文件路径")
    error: Optional[str] = Field(default=None, description="错误信息")


class VoiceChatRequest(BaseModel):
    """语音聊天请求"""
    audio_data: str = Field(..., description="Base64编码的音频数据")
    format: str = Field(default="wav", description="音频格式")


class VoiceChatResponse(BaseModel):
    """语音聊天响应"""
    success: bool = Field(default=True, description="是否成功")
    text: str = Field(default="", description="识别出的文本")
    reply: str = Field(default="", description="回复内容")
    audio_path: Optional[str] = Field(default=None, description="回复音频路径")
    error: Optional[str] = Field(default=None, description="错误信息")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = "ok"
    version: str
    services: dict


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error: str
    detail: Optional[str] = None
