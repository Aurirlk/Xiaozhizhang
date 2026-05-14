"""
CRM 数据库模型
定义用户、交互记录、用户偏好标签表
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON, Boolean, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    """生成 UUID 字符串"""
    return str(uuid.uuid4())


class User(Base):
    """
    用户表
    存储用户基本信息
    """
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), nullable=True, comment="用户名")
    phone = Column(String(20), nullable=True, unique=True, comment="手机号")
    email = Column(String(100), nullable=True, comment="邮箱")
    nickname = Column(String(50), nullable=True, comment="昵称")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    
    # 来源信息
    source = Column(String(50), default="web", comment="来源渠道: web/wechat/app")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    last_active_at = Column(DateTime, default=datetime.utcnow, comment="最后活跃时间")
    
    # 关系
    interactions = relationship("Interaction", back_populates="user", cascade="all, delete-orphan")
    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, phone={self.phone})>"


class Interaction(Base):
    """
    交互记录表
    存储每次对话的完整记录
    """
    __tablename__ = "interactions"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 对话内容
    user_message = Column(Text, nullable=False, comment="用户消息")
    assistant_message = Column(Text, nullable=False, comment="助手回复")
    
    # 语音相关
    audio_input_path = Column(String(500), nullable=True, comment="用户语音文件路径")
    audio_output_path = Column(String(500), nullable=True, comment="助手语音文件路径")
    
    # 元数据
    asr_text = Column(Text, nullable=True, comment="ASR识别原文")
    llm_model = Column(String(50), nullable=True, comment="使用的LLM模型")
    tts_model = Column(String(50), nullable=True, comment="使用的TTS模型")
    
    # 意图识别
    intent = Column(String(50), nullable=True, comment="用户意图: weather/news/search/knowledge/chat")
    intent_confidence = Column(Integer, nullable=True, comment="意图置信度 (0-100)")
    intent_source = Column(String(20), nullable=True, comment="意图来源: keyword/llm")
    entities = Column(JSON, nullable=True, comment="提取的实体信息")
    
    # 耗时统计 (毫秒)
    asr_latency_ms = Column(Integer, nullable=True, comment="ASR耗时")
    llm_latency_ms = Column(Integer, nullable=True, comment="LLM耗时")
    tts_latency_ms = Column(Integer, nullable=True, comment="TTS耗时")
    total_latency_ms = Column(Integer, nullable=True, comment="总耗时")
    
    # CRM 分析结果
    crm_analyzed = Column(Boolean, default=False, comment="是否已进行CRM分析")
    crm_extracted_data = Column(JSON, nullable=True, comment="CRM提取的JSON数据")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="对话时间")
    
    # 关系
    user = relationship("User", back_populates="interactions")
    
    def __repr__(self):
        return f"<Interaction(id={self.id}, user_id={self.user_id})>"


class Conversation(Base):
    """
    会话表
    存储用户的对话会话
    """
    __tablename__ = "conversations"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, comment="用户ID")
    
    # 会话信息
    title = Column(String(200), nullable=True, comment="会话标题")
    
    # 状态
    is_active = Column(Boolean, default=True, comment="是否活跃")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title})>"


class ChatMessage(Base):
    """
    聊天消息表
    存储单条消息
    """
    __tablename__ = "chat_messages"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False, comment="会话ID")
    
    # 消息内容
    role = Column(String(20), nullable=False, comment="角色: user/assistant/system")
    content = Column(Text, nullable=False, comment="消息内容")
    
    # 语音相关
    audio_path = Column(String(500), nullable=True, comment="语音文件路径")
    
    # 元数据
    model = Column(String(50), nullable=True, comment="使用的模型")
    tokens = Column(Integer, nullable=True, comment="token 数量")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    
    # 关系
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, role={self.role})>"


class UserProfile(Base):
    """
    用户画像表
    存储从对话中提取的用户偏好、特征信息
    """
    __tablename__ = "user_profiles"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, unique=True, comment="用户ID")
    
    # 基本信息
    name = Column(String(50), nullable=True, comment="姓名")
    gender = Column(String(10), nullable=True, comment="性别")
    age_range = Column(String(20), nullable=True, comment="年龄段")
    occupation = Column(String(50), nullable=True, comment="职业")
    city = Column(String(50), nullable=True, comment="所在城市")
    
    # 偏好信息 (JSON格式存储)
    preferences = Column(JSON, nullable=True, comment="用户偏好")
    # 示例: {"hobbies": ["阅读", "音乐"], "food": ["咖啡", "甜食"], "music": ["流行"]}
    
    # 意向信息
    intent = Column(String(100), nullable=True, comment="用户意向")
    budget_range = Column(String(50), nullable=True, comment="预算范围")
    
    # 标签
    tags = Column(JSON, nullable=True, comment="用户标签")
    # 示例: ["高意向", "价格敏感", "回头客"]
    
    # 备注
    notes = Column(Text, nullable=True, comment="备注信息")
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    
    # 关系
    user = relationship("User", back_populates="profile")
    
    def __repr__(self):
        return f"<UserProfile(user_id={self.user_id}, name={self.name})>"
