"""
RAG 检索服务
提供知识库检索和查询功能
支持 ChromaDB 向量检索 + SQLite 全文检索
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.knowledge.document_loader import DocumentLoader
from app.knowledge.sqlite_store import SQLiteStore
from app.utils.logger import logger


class RAGService:
    """
    RAG 检索服务
    
    提供知识库文档加载、存储和检索功能
    优先使用 ChromaDB 向量检索，回退到 SQLite 全文检索
    """
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.document_loader = DocumentLoader()
            self.sqlite_store = SQLiteStore()
            self._vector_store = None
            self._initialized = True
    
    def _get_vector_store(self):
        """延迟加载向量存储"""
        if self._vector_store is None:
            try:
                from app.knowledge.vector_store import vector_store
                self._vector_store = vector_store
            except Exception as e:
                logger.warning(f"[RAG] ChromaDB 不可用，使用 SQLite: {e}")
        return self._vector_store
    
    async def load_knowledge_base(self, force_reload: bool = False) -> int:
        """
        加载知识库文档
        
        Args:
            force_reload: 是否强制重新加载
            
        Returns:
            加载的文档数量
        """
        knowledge_dir = "data/Knowledge"
        
        if not os.path.exists(knowledge_dir):
            logger.warning(f"[RAG] 知识库目录不存在: {knowledge_dir}")
            os.makedirs(knowledge_dir, exist_ok=True)
            return 0
        
        # 检查是否需要重新加载
        if not force_reload:
            sqlite_count = self.sqlite_store.get_document_count()
            vector_store = self._get_vector_store()
            vector_count = vector_store.get_stats().get("document_count", 0) if vector_store else 0
            
            if sqlite_count > 0 or vector_count > 0:
                logger.info(f"[RAG] 知识库已加载，SQLite: {sqlite_count}, Vector: {vector_count}")
                return max(sqlite_count, vector_count)
        
        # 清空旧数据
        if force_reload:
            self.sqlite_store.clear()
            vector_store = self._get_vector_store()
            if vector_store:
                vector_store.clear()
            logger.info("[RAG] 已清空旧数据")
        
        # 加载文档
        documents = self.document_loader.load_directory(knowledge_dir)
        
        if documents:
            # 存储到 SQLite
            sqlite_count = self.sqlite_store.add_documents(documents)
            
            # 存储到向量库
            vector_store = self._get_vector_store()
            vector_count = 0
            if vector_store:
                vector_count = vector_store.add_documents(documents)
            
            count = max(sqlite_count, vector_count)
            logger.info(f"[RAG] 加载完成，SQLite: {sqlite_count}, Vector: {vector_count}")
            return count
        
        return 0
    
    async def search(
        self, 
        query: str, 
        limit: int = 5,
        use_vector: bool = True
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            query: 查询内容
            limit: 返回结果数量
            use_vector: 是否优先使用向量检索
            
        Returns:
            搜索结果列表
        """
        results = []
        
        # 优先使用向量检索
        if use_vector:
            vector_store = self._get_vector_store()
            if vector_store:
                results = vector_store.search(query, n_results=limit)
        
        # 向量检索无结果或不可用时，回退到 SQLite
        if not results:
            results = self.sqlite_store.search(query, limit=limit)
        
        logger.info(f"[RAG] 搜索: '{query}', 结果数: {len(results)}")
        return results
    
    async def search_with_context(
        self, 
        query: str, 
        limit: int = 3
    ) -> str:
        """
        搜索并返回上下文文本
        
        Args:
            query: 查询内容
            limit: 返回结果数量
            
        Returns:
            拼接后的上下文文本
        """
        # 优先使用向量检索
        vector_store = self._get_vector_store()
        if vector_store:
            context = vector_store.search_with_context(query, n_results=limit)
            if context:
                return context
        
        # 回退到 SQLite
        results = self.sqlite_store.search(query, limit=limit)
        
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get("source", "未知来源")
            content = result.get("content", "")
            context_parts.append(f"[来源{i}: {source}]\n{content}")
        
        return "\n\n".join(context_parts)
    
    async def add_document(self, file_path: str) -> bool:
        """
        添加单个文档到知识库
        
        Args:
            file_path: 文件路径
            
        Returns:
            是否成功
        """
        try:
            documents = self.document_loader.load_file(file_path)
            if documents:
                # 存储到 SQLite
                self.sqlite_store.add_documents(documents)
                
                # 存储到向量库
                vector_store = self._get_vector_store()
                if vector_store:
                    vector_store.add_documents(documents)
                
                logger.info(f"[RAG] 添加文档: {file_path}, 分块数: {len(documents)}")
                return True
            return False
        except Exception as e:
            logger.error(f"[RAG] 添加文档失败: {e}")
            return False
    
    async def add_documents_from_text(
        self, 
        text: str, 
        source: str = "manual"
    ) -> int:
        """
        从文本添加文档
        
        Args:
            text: 文本内容
            source: 来源标识
            
        Returns:
            添加的文档数量
        """
        documents = self.document_loader._split_text(text)
        
        doc_list = []
        for i, chunk in enumerate(documents):
            doc_list.append({
                "content": chunk,
                "metadata": {
                    "source": source,
                    "chunk_index": i,
                    "total_chunks": len(documents)
                }
            })
        
        # 存储到 SQLite
        sqlite_count = self.sqlite_store.add_documents(doc_list)
        
        # 存储到向量库
        vector_store = self._get_vector_store()
        vector_count = 0
        if vector_store:
            vector_count = vector_store.add_documents(doc_list)
        
        return max(sqlite_count, vector_count)
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        sqlite_stats = {
            "total_documents": self.sqlite_store.get_document_count(),
            "sources": self.sqlite_store.get_source_stats()
        }
        
        vector_store = self._get_vector_store()
        vector_stats = vector_store.get_stats() if vector_store else {"status": "disabled"}
        
        return {
            "sqlite": sqlite_stats,
            "vector": vector_stats,
            "supported_formats": self.document_loader.get_supported_formats(),
            "knowledge_dir": "data/Knowledge"
        }
    
    async def clear(self):
        """清空知识库"""
        self.sqlite_store.clear()
        
        vector_store = self._get_vector_store()
        if vector_store:
            vector_store.clear()
        
        logger.info("[RAG] 知识库已清空")


# 全局 RAG 服务实例
rag_service = RAGService()
