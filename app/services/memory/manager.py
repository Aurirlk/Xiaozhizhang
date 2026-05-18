"""
记忆管理器
支持短期记忆（会话）和长期记忆（向量数据库）
"""
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.utils.logger import logger


class MemoryManager:
    """
    记忆管理器
    
    支持：
    - 短期记忆：当前会话的对话历史
    - 长期记忆：向量数据库存储的关键信息
    - 记忆总结：自动总结对话要点
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._short_term: Dict[str, List[Dict]] = {}
            cls._instance._long_term_db = None
        return cls._instance
    
    def __init__(self):
        self._init_long_term_db()
        logger.info("[Memory] 记忆系统初始化完成")
    
    def _init_long_term_db(self):
        """初始化长期记忆数据库"""
        try:
            # 使用 ChromaDB 存储长期记忆
            import chromadb
            
            persist_dir = "data/memory_db"
            os.makedirs(persist_dir, exist_ok=True)
            
            self._long_term_db = chromadb.PersistentClient(path=persist_dir)
            self._collection = self._long_term_db.get_or_create_collection(
                name="long_term_memory",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"[Memory] 长期记忆数据库初始化完成")
        except Exception as e:
            logger.error(f"[Memory] 长期记忆数据库初始化失败: {e}")
            self._long_term_db = None
    
    # ==================== 短期记忆 ====================
    
    def add_short_term(self, session_id: str, role: str, content: str):
        """添加短期记忆"""
        if session_id not in self._short_term:
            self._short_term[session_id] = []
        
        self._short_term[session_id].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        
        # 保持滑动窗口
        max_messages = 20  # 最多保留20条消息
        if len(self._short_term[session_id]) > max_messages:
            self._short_term[session_id] = self._short_term[session_id][-max_messages:]
    
    def get_short_term(self, session_id: str, limit: int = 10) -> List[Dict]:
        """获取短期记忆"""
        return self._short_term.get(session_id, [])[-limit:]
    
    def clear_short_term(self, session_id: str):
        """清空短期记忆"""
        if session_id in self._short_term:
            del self._short_term[session_id]
    
    # ==================== 长期记忆 ====================
    
    async def add_long_term(self, user_id: str, content: str, metadata: Dict = None):
        """添加长期记忆"""
        if not self._collection:
            logger.warning("[Memory] 长期记忆数据库未初始化")
            return
        
        try:
            memory_id = f"memory_{uuid.uuid4().hex[:8]}"
            
            self._collection.add(
                ids=[memory_id],
                documents=[content],
                metadatas=[{
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat(),
                    **(metadata or {})
                }]
            )
            
            logger.info(f"[Memory] 添加长期记忆: {memory_id}")
            
        except Exception as e:
            logger.error(f"[Memory] 添加长期记忆失败: {e}")
    
    async def search_long_term(self, query: str, user_id: Optional[str] = None, limit: int = 5) -> List[Dict]:
        """搜索长期记忆"""
        if not self._collection:
            return []
        
        try:
            where = {"user_id": user_id} if user_id else None
            
            results = self._collection.query(
                query_texts=[query],
                n_results=limit,
                where=where
            )
            
            memories = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    memories.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "score": results["distances"][0][i] if results["distances"] else 0
                    })
            
            return memories
            
        except Exception as e:
            logger.error(f"[Memory] 搜索长期记忆失败: {e}")
            return []
    
    async def summarize_conversation(self, session_id: str) -> str:
        """总结对话内容"""
        messages = self.get_short_term(session_id)
        
        if not messages:
            return "暂无对话内容"
        
        # 构建对话文本
        conversation = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages
        ])
        
        # 使用 LLM 生成总结
        try:
            from app.services.factory import ServiceFactory
            llm_service = ServiceFactory.create_llm()
            
            prompt = f"""请总结以下对话的要点，用简洁的语言概括：

{conversation}

总结："""
            
            summary = await llm_service.chat(prompt)
            
            # 保存到长期记忆
            await self.add_long_term(
                user_id=session_id,
                content=summary,
                metadata={"type": "conversation_summary"}
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"[Memory] 对话总结失败: {e}")
            return "总结生成失败"
    
    async def recall_memory(self, query: str, user_id: Optional[str] = None) -> str:
        """回忆相关记忆"""
        memories = await self.search_long_term(query, user_id)
        
        if not memories:
            return "没有找到相关记忆"
        
        # 构建记忆上下文
        context_parts = []
        for mem in memories[:3]:
            context_parts.append(f"- {mem['content']}")
        
        return "\n".join(context_parts)
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """获取记忆统计"""
        total_short_term = sum(len(msgs) for msgs in self._short_term.values())
        total_sessions = len(self._short_term)
        
        long_term_count = 0
        if self._collection:
            try:
                long_term_count = self._collection.count()
            except:
                pass
        
        return {
            "short_term": {
                "total_messages": total_short_term,
                "active_sessions": total_sessions
            },
            "long_term": {
                "total_memories": long_term_count
            }
        }


# 全局记忆管理器实例
memory_manager = MemoryManager()
