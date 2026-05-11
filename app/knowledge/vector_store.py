"""
ChromaDB 向量存储模块
提供基于向量的语义检索功能
"""
import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from app.utils.logger import logger


class VectorStore:
    """
    ChromaDB 向量存储服务
    
    提供文档向量化存储和语义检索
    """
    
    _instance = None
    _client = None
    _collection = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._client is None:
            self._init_client()
    
    def _init_client(self):
        """初始化 ChromaDB 客户端"""
        try:
            import chromadb
            
            # 从配置获取 ChromaDB 设置
            chroma_host = os.getenv("CHROMA_HOST", "localhost")
            chroma_port = int(os.getenv("CHROMA_PORT", "8000"))
            
            # 尝试连接远程 ChromaDB，失败则使用本地
            try:
                self._client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
                logger.info(f"[VectorStore] 连接远程 ChromaDB: {chroma_host}:{chroma_port}")
            except Exception:
                # 本地模式
                persist_dir = "data/chroma_db"
                os.makedirs(persist_dir, exist_ok=True)
                self._client = chromadb.PersistentClient(path=persist_dir)
                logger.info(f"[VectorStore] 使用本地 ChromaDB: {persist_dir}")
            
            # 获取或创建集合
            self._collection = self._client.get_or_create_collection(
                name="neuvox_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            
            logger.info(f"[VectorStore] ChromaDB 初始化完成，文档数: {self._collection.count()}")
            
        except ImportError:
            logger.error("[VectorStore] chromadb 未安装，请运行: pip install chromadb")
        except Exception as e:
            logger.error(f"[VectorStore] ChromaDB 初始化失败: {e}")
    
    def add_documents(
        self, 
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        批量添加文档到向量库
        
        Args:
            documents: 文档列表，每个文档包含 content 和 metadata
            batch_size: 批次大小
            
        Returns:
            添加的文档数量
        """
        if not self._collection:
            logger.error("[VectorStore] ChromaDB 未初始化")
            return 0
        
        try:
            # 准备数据
            ids = []
            contents = []
            metadatas = []
            
            for doc in documents:
                doc_id = f"doc_{hash(doc['content'])}_{len(ids)}"
                ids.append(doc_id)
                contents.append(doc["content"])
                metadatas.append(doc.get("metadata", {}))
            
            # 分批添加
            total_added = 0
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i+batch_size]
                batch_contents = contents[i:i+batch_size]
                batch_metadatas = metadatas[i:i+batch_size]
                
                self._collection.add(
                    ids=batch_ids,
                    documents=batch_contents,
                    metadatas=batch_metadatas
                )
                total_added += len(batch_ids)
            
            logger.info(f"[VectorStore] 添加文档: {total_added} 条")
            return total_added
            
        except Exception as e:
            logger.error(f"[VectorStore] 添加文档失败: {e}")
            return 0
    
    def search(
        self, 
        query: str, 
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            where: 过滤条件
            
        Returns:
            搜索结果列表
        """
        if not self._collection:
            logger.error("[VectorStore] ChromaDB 未初始化")
            return []
        
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )
            
            # 格式化结果
            formatted_results = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    formatted_results.append({
                        "content": doc,
                        "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                        "distance": results["distances"][0][i] if results["distances"] else 0
                    })
            
            logger.info(f"[VectorStore] 搜索: '{query}', 结果数: {len(formatted_results)}")
            return formatted_results
            
        except Exception as e:
            logger.error(f"[VectorStore] 搜索失败: {e}")
            return []
    
    def search_with_context(
        self, 
        query: str, 
        n_results: int = 3
    ) -> str:
        """
        搜索并返回上下文文本
        
        Args:
            query: 查询文本
            n_results: 返回结果数量
            
        Returns:
            拼接后的上下文文本
        """
        results = self.search(query, n_results=n_results)
        
        if not results:
            return ""
        
        context_parts = []
        for i, result in enumerate(results, 1):
            source = result.get("metadata", {}).get("source", "未知来源")
            content = result.get("content", "")
            score = result.get("distance", 0)
            context_parts.append(f"[来源{i}: {source} (相关度: {score:.2f})]\n{content}")
        
        return "\n\n".join(context_parts)
    
    def delete_by_source(self, source: str):
        """按来源删除文档"""
        if not self._collection:
            return
        
        try:
            # 查询该来源的所有文档
            results = self._collection.get(
                where={"source": source}
            )
            
            if results and results["ids"]:
                self._collection.delete(ids=results["ids"])
                logger.info(f"[VectorStore] 删除来源 '{source}' 的文档: {len(results['ids'])} 条")
                
        except Exception as e:
            logger.error(f"[VectorStore] 删除文档失败: {e}")
    
    def clear(self):
        """清空向量库"""
        if not self._collection:
            return
        
        try:
            # 获取所有文档 ID
            results = self._collection.get()
            if results and results["ids"]:
                self._collection.delete(ids=results["ids"])
            logger.info("[VectorStore] 已清空向量库")
        except Exception as e:
            logger.error(f"[VectorStore] 清空失败: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取向量库统计信息"""
        if not self._collection:
            return {"status": "not_initialized"}
        
        try:
            count = self._collection.count()
            return {
                "status": "ready",
                "document_count": count,
                "collection_name": "neuvox_knowledge"
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}


# 全局向量存储实例
vector_store = VectorStore()
