"""
历史记录管理器
使用 JSON 文件保存对话历史
"""
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from app.utils.logger import logger


class HistoryManager:
    """
    历史记录管理器
    
    功能：
    - 保存对话历史到 JSON 文件
    - 加载对话历史
    - 按会话管理历史
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._history_dir = "data/history"
        return cls._instance
    
    def __init__(self):
        # 确保目录存在
        os.makedirs(self._history_dir, exist_ok=True)
        logger.info(f"[History] 历史记录管理器初始化完成，目录: {self._history_dir}")
    
    async def save_history(
        self, 
        session_id: str, 
        user_id: str,
        messages: List[Dict[str, str]],
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        保存对话历史
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            messages: 消息列表
            metadata: 元数据
            
        Returns:
            是否保存成功
        """
        try:
            history_data = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": messages,
                "metadata": metadata or {}
            }
            
            file_path = os.path.join(self._history_dir, f"{session_id}.json")
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(history_data, ensure_ascii=False, indent=2))
            
            logger.info(f"[History] 保存历史: {session_id}, 消息数: {len(messages)}")
            return True
            
        except Exception as e:
            logger.error(f"[History] 保存历史失败: {e}")
            return False
    
    async def load_history(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        加载对话历史
        
        Args:
            session_id: 会话 ID
            
        Returns:
            历史数据
        """
        file_path = os.path.join(self._history_dir, f"{session_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"[History] 加载历史失败: {e}")
            return None
    
    async def add_message(
        self, 
        session_id: str, 
        user_id: str,
        role: str, 
        content: str,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        添加消息到历史
        
        Args:
            session_id: 会话 ID
            user_id: 用户 ID
            role: 角色 (user/assistant)
            content: 消息内容
            metadata: 元数据
            
        Returns:
            是否添加成功
        """
        # 加载现有历史
        history = await self.load_history(session_id)
        
        if history is None:
            history = {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": datetime.now().isoformat(),
                "messages": [],
                "metadata": {}
            }
        
        # 添加新消息
        history["messages"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 更新元数据
        if metadata:
            history["metadata"].update(metadata)
        
        history["updated_at"] = datetime.now().isoformat()
        
        # 保存
        file_path = os.path.join(self._history_dir, f"{session_id}.json")
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(history, ensure_ascii=False, indent=2))
        
        logger.info(f"[History] 添加消息: {session_id}, 角色: {role}")
        return True
    
    async def get_messages(self, session_id: str, limit: int = 10) -> List[Dict[str, str]]:
        """
        获取消息列表
        
        Args:
            session_id: 会话 ID
            limit: 返回消息数量
            
        Returns:
            消息列表
        """
        history = await self.load_history(session_id)
        
        if history is None:
            return []
        
        return history.get("messages", [])[-limit:]
    
    async def get_all_sessions(self) -> List[Dict[str, Any]]:
        """获取所有会话列表"""
        sessions = []
        
        for file_name in os.listdir(self._history_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(self._history_dir, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        sessions.append({
                            "session_id": data.get("session_id"),
                            "user_id": data.get("user_id"),
                            "message_count": len(data.get("messages", [])),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at")
                        })
                except Exception as e:
                    logger.error(f"[History] 读取会话失败: {file_name}, {e}")
        
        return sessions
    
    async def delete_history(self, session_id: str) -> bool:
        """删除对话历史"""
        file_path = os.path.join(self._history_dir, f"{session_id}.json")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[History] 删除历史: {session_id}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取历史统计"""
        files = [f for f in os.listdir(self._history_dir) if f.endswith(".json")]
        return {
            "total_sessions": len(files),
            "directory": self._history_dir
        }


# 全局历史管理器实例
history_manager = HistoryManager()
