"""
SQLite 存储模块
用于存储文档块和知识库索引
"""
import sqlite3
import json
from typing import List, Dict, Optional, Any
from pathlib import Path

from app.utils.logger import logger


class SQLiteStore:
    """
    SQLite 存储服务
    
    存储文档块和知识库索引
    """
    
    def __init__(self, db_path: str = "data/knowledge.db"):
        """
        初始化 SQLite 存储
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        
        # 确保目录存在
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    source TEXT,
                    file_path TEXT,
                    chunk_index INTEGER,
                    total_chunks INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 创建全文搜索索引
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts 
                USING fts5(content, source)
            """)
            
            conn.commit()
            
        logger.info(f"[SQLiteStore] 数据库初始化完成: {self.db_path}")
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> int:
        """
        批量添加文档
        
        Args:
            documents: 文档块列表
            
        Returns:
            添加的文档数量
        """
        with sqlite3.connect(self.db_path) as conn:
            count = 0
            
            for doc in documents:
                try:
                    conn.execute(
                        "INSERT INTO documents (content, source, file_path, chunk_index, total_chunks) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (
                            doc["content"],
                            doc.get("metadata", {}).get("source"),
                            doc.get("metadata", {}).get("file_path"),
                            doc.get("metadata", {}).get("chunk_index"),
                            doc.get("metadata", {}).get("total_chunks")
                        )
                    )
                    
                    # 更新全文搜索索引
                    conn.execute(
                        "INSERT INTO documents_fts(content, source) VALUES (?, ?)",
                        (doc["content"], doc.get("metadata", {}).get("source"))
                    )
                    
                    count += 1
                    
                except Exception as e:
                    logger.error(f"[SQLiteStore] 添加文档失败: {e}")
            
            conn.commit()
            
        logger.info(f"[SQLiteStore] 添加文档: {count} 条")
        return count
    
    def search(
        self, 
        query: str, 
        limit: int = 5,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        全文搜索
        
        Args:
            query: 搜索查询
            limit: 返回结果数量
            min_score: 最小相关度分数
            
        Returns:
            搜索结果列表
        """
        with sqlite3.connect(self.db_path) as conn:
            # 使用 FTS5 全文搜索
            try:
                cursor = conn.execute(
                    "SELECT content, source, rank "
                    "FROM documents_fts "
                    "JOIN documents ON documents_fts.rowid = documents.id "
                    "WHERE documents_fts MATCH ? "
                    "ORDER BY rank "
                    "LIMIT ?",
                    (query, limit)
                )
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        "content": row[0],
                        "source": row[1],
                        "score": abs(row[2])  # rank 值越小越相关
                    })
                
                return results
                
            except Exception as e:
                logger.error(f"[SQLiteStore] 搜索失败: {e}")
                return []
    
    def keyword_search(
        self, 
        keyword: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        关键词搜索（LIKE 查询）
        
        Args:
            keyword: 关键词
            limit: 返回结果数量
            
        Returns:
            搜索结果列表
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT content, source FROM documents "
                "WHERE content LIKE ? "
                "LIMIT ?",
                (f"%{keyword}%", limit)
            )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "content": row[0],
                    "source": row[1]
                })
            
            return results
    
    def get_document_count(self) -> int:
        """获取文档总数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM documents")
            return cursor.fetchone()[0]
    
    def get_source_stats(self) -> Dict[str, int]:
        """获取各来源文档统计"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT source, COUNT(*) FROM documents GROUP BY source"
            )
            return {row[0]: row[1] for row in cursor.fetchall()}
    
    def clear(self):
        """清空所有文档"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM documents")
            conn.execute("DELETE FROM documents_fts")
            conn.commit()
        
        logger.info("[SQLiteStore] 已清空所有文档")
    
    def delete_by_source(self, source: str):
        """按来源删除文档"""
        with sqlite3.connect(self.db_path) as conn:
            # 获取要删除的文档 ID
            cursor = conn.execute(
                "SELECT id FROM documents WHERE source = ?", (source,)
            )
            ids = [row[0] for row in cursor.fetchall()]
            
            if ids:
                placeholders = ",".join(["?"] * len(ids))
                conn.execute(f"DELETE FROM documents WHERE id IN ({placeholders})", ids)
                
                # 删除 FTS 索引
                for doc_id in ids:
                    conn.execute(
                        "DELETE FROM documents_fts WHERE rowid = ?", (doc_id,)
                    )
            
            conn.commit()
            
        logger.info(f"[SQLiteStore] 已删除来源 '{source}' 的文档: {len(ids)} 条")
