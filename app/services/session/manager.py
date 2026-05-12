"""
Redis 会话管理器
提供基于 Redis 的会话持久化存储
"""
import json
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

from app.utils.logger import logger


class RedisSessionManager:
    """
    Redis 会话管理器
    
    功能：
    - 会话历史持久化存储
    - 会话超时管理
    - 滑动窗口历史记录
    """
    
    _instance = None
    _redis = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._redis is None:
            self._init_redis()
    
    def _init_redis(self):
        """初始化 Redis 连接"""
        try:
            import redis.asyncio as aioredis
            
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis = aioredis.from_url(redis_url, decode_responses=True)
            
            logger.info(f"[RedisSession] 连接 Redis: {redis_url}")
            
        except ImportError:
            logger.warning("[RedisSession] redis 未安装，使用内存存储")
            self._redis = None
        except Exception as e:
            logger.error(f"[RedisSession] Redis 连接失败: {e}")
            self._redis = None
    
    async def get_history(self, session_id: str, max_history: int = 10) -> List[Dict[str, str]]:
        """
        获取会话历史
        
        Args:
            session_id: 会话 ID
            max_history: 最多保留轮数
            
        Returns:
            历史消息列表
        """
        if not self._redis:
            return []
        
        try:
            key = f"session:{session_id}:history"
            history_json = await self._redis.get(key)
            
            if history_json:
                history = json.loads(history_json)
                # 滑动窗口：保留最近 N 轮（每轮2条消息）
                max_messages = max_history * 2
                if len(history) > max_messages:
                    history = history[-max_messages:]
                return history
            
            return []
            
        except Exception as e:
            logger.error(f"[RedisSession] 获取历史失败: {e}")
            return []
    
    async def add_message(self, session_id: str, role: str, content: str, max_history: int = 10):
        """
        添加消息到历史
        
        Args:
            session_id: 会话 ID
            role: 角色 (user/assistant)
            content: 消息内容
            max_history: 最多保留轮数
        """
        if not self._redis:
            return
        
        try:
            key = f"session:{session_id}:history"
            
            # 获取现有历史
            history_json = await self._redis.get(key)
            history = json.loads(history_json) if history_json else []
            
            # 添加新消息
            history.append({"role": role, "content": content})
            
            # 滑动窗口
            max_messages = max_history * 2
            if len(history) > max_messages:
                history = history[-max_messages:]
            
            # 保存
            await self._redis.set(key, json.dumps(history, ensure_ascii=False))
            
            # 设置过期时间（24小时）
            await self._redis.expire(key, 86400)
            
        except Exception as e:
            logger.error(f"[RedisSession] 添加消息失败: {e}")
    
    async def clear_history(self, session_id: str):
        """清空会话历史"""
        if not self._redis:
            return
        
        try:
            key = f"session:{session_id}:history"
            await self._redis.delete(key)
            logger.info(f"[RedisSession] 清空会话: {session_id}")
        except Exception as e:
            logger.error(f"[RedisSession] 清空历史失败: {e}")
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        if not self._redis:
            return {"exists": False}
        
        try:
            key = f"session:{session_id}:history"
            history_json = await self._redis.get(key)
            ttl = await self._redis.ttl(key)
            
            return {
                "exists": history_json is not None,
                "message_count": len(json.loads(history_json)) if history_json else 0,
                "ttl_seconds": ttl
            }
        except Exception as e:
            logger.error(f"[RedisSession] 获取会话信息失败: {e}")
            return {"exists": False}
    
    async def close(self):
        """关闭 Redis 连接"""
        if self._redis:
            await self._redis.close()


# 内存会话管理器（Redis 不可用时的降级方案）
class MemorySessionManager:
    """
    内存会话管理器
    当 Redis 不可用时使用
    """
    
    def __init__(self):
        self._sessions: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    
    async def get_history(self, session_id: str, max_history: int = 10) -> List[Dict[str, str]]:
        """获取会话历史"""
        history = self._sessions.get(session_id, [])
        max_messages = max_history * 2
        if len(history) > max_messages:
            history = history[-max_messages:]
        return history
    
    async def add_message(self, session_id: str, role: str, content: str, max_history: int = 10):
        """添加消息到历史"""
        if session_id not in self._sessions:
            self._sessions[session_id] = []
        
        self._sessions[session_id].append({"role": role, "content": content})
        
        # 滑动窗口
        max_messages = max_history * 2
        if len(self._sessions[session_id]) > max_messages:
            self._sessions[session_id] = self._sessions[session_id][-max_messages:]
    
    async def clear_history(self, session_id: str):
        """清空会话历史"""
        if session_id in self._sessions:
            del self._sessions[session_id]
    
    async def get_session_info(self, session_id: str) -> Dict[str, Any]:
        """获取会话信息"""
        history = self._sessions.get(session_id, [])
        return {
            "exists": len(history) > 0,
            "message_count": len(history),
            "ttl_seconds": -1  # 永不过期
        }
    
    async def close(self):
        """关闭连接"""
        pass


from collections import defaultdict


def get_session_manager():
    """获取会话管理器（自动选择 Redis 或内存）"""
    redis_url = os.getenv("REDIS_URL")
    
    if redis_url:
        manager = RedisSessionManager()
        if manager._redis:
            return manager
    
    return MemorySessionManager()
