"""
Embedding 服务
提供文本向量化功能
"""
import os
from typing import List, Optional
import numpy as np

from app.utils.logger import logger
from app.utils.config_loader import config


class EmbeddingService:
    """
    Embedding 服务
    
    支持：
    - sentence-transformers 本地模型
    - 文本向量化
    """
    
    _instance = None
    _model = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """加载 Embedding 模型"""
        try:
            from sentence_transformers import SentenceTransformer
            
            embedding_config = config.get("Embedding", default={})
            model_name = embedding_config.get("model", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            
            logger.info(f"[Embedding] 加载模型: {model_name}")
            self._model = SentenceTransformer(model_name)
            logger.info("[Embedding] 模型加载完成")
            
        except ImportError:
            logger.error("[Embedding] sentence-transformers 未安装")
            self._model = None
        except Exception as e:
            logger.error(f"[Embedding] 模型加载失败: {e}")
            self._model = None
    
    def encode(self, texts: List[str]) -> np.ndarray:
        """
        将文本转换为向量
        
        Args:
            texts: 文本列表
            
        Returns:
            向量数组
        """
        if self._model is None:
            raise ValueError("Embedding 模型未加载")
        
        return self._model.encode(texts)
    
    def encode_single(self, text: str) -> np.ndarray:
        """
        将单个文本转换为向量
        
        Args:
            text: 文本
            
        Returns:
            向量
        """
        return self.encode([text])[0]
    
    def cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        计算余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            相似度 (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def is_available(self) -> bool:
        """检查模型是否可用"""
        return self._model is not None


# 全局 Embedding 服务实例
embedding_service = EmbeddingService()
