"""
对话历史服务
管理用户的对话会话和消息
"""
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm_models import User, Conversation, ChatMessage
from app.utils.logger import logger


class ChatHistoryService:
    """对话历史服务"""
    
    async def get_or_create_user(
        self, 
        db: AsyncSession, 
        user_id: Optional[str] = None,
        source: str = "api"
    ) -> User:
        """获取或创建用户"""
        if user_id:
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                user.last_active_at = datetime.utcnow()
                await db.commit()
                return user
        
        # 创建新用户
        user = User(source=source)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    async def get_or_create_conversation(
        self, 
        db: AsyncSession, 
        user_id: str,
        conversation_id: Optional[str] = None
    ) -> Conversation:
        """获取或创建会话"""
        if conversation_id:
            result = await db.execute(
                select(Conversation).where(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            )
            conv = result.scalar_one_or_none()
            if conv:
                conv.updated_at = datetime.utcnow()
                await db.commit()
                return conv
        
        # 创建新会话
        conv = Conversation(user_id=user_id)
        db.add(conv)
        await db.commit()
        await db.refresh(conv)
        return conv
    
    async def add_message(
        self, 
        db: AsyncSession, 
        conversation_id: str,
        role: str,
        content: str,
        audio_path: Optional[str] = None,
        model: Optional[str] = None,
        tokens: Optional[int] = None
    ) -> ChatMessage:
        """添加消息"""
        message = ChatMessage(
            conversation_id=conversation_id,
            role=role,
            content=content,
            audio_path=audio_path,
            model=model,
            tokens=tokens
        )
        db.add(message)
        
        # 更新会话时间
        result = await db.execute(
            select(Conversation).where(Conversation.id == conversation_id)
        )
        conv = result.scalar_one_or_none()
        if conv:
            conv.updated_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(message)
        return message
    
    async def get_conversation_history(
        self, 
        db: AsyncSession, 
        conversation_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """获取会话历史"""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.created_at)
            .limit(limit)
        )
        messages = result.scalars().all()
        
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "audio_path": msg.audio_path,
                "created_at": msg.created_at.isoformat()
            }
            for msg in messages
        ]
    
    async def get_user_conversations(
        self, 
        db: AsyncSession, 
        user_id: str,
        limit: int = 20
    ) -> List[Dict]:
        """获取用户的会话列表"""
        result = await db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
        )
        conversations = result.scalars().all()
        
        return [
            {
                "id": conv.id,
                "title": conv.title,
                "is_active": conv.is_active,
                "created_at": conv.created_at.isoformat(),
                "updated_at": conv.updated_at.isoformat()
            }
            for conv in conversations
        ]
    
    async def get_context_for_llm(
        self, 
        db: AsyncSession, 
        conversation_id: str,
        max_turns: int = 10
    ) -> List[Dict]:
        """获取用于 LLM 的对话上下文"""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .where(ChatMessage.role.in_(["user", "assistant"]))
            .order_by(desc(ChatMessage.created_at))
            .limit(max_turns * 2)
        )
        messages = result.scalars().all()
        
        # 反转顺序（从旧到新）
        messages = list(reversed(messages))
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
    
    async def delete_conversation(
        self, 
        db: AsyncSession, 
        conversation_id: str,
        user_id: str
    ) -> bool:
        """删除会话"""
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user_id
            )
        )
        conv = result.scalar_one_or_none()
        
        if conv:
            await db.delete(conv)
            await db.commit()
            return True
        
        return False


# 全局服务实例
chat_history_service = ChatHistoryService()
