"""
声纹识别器
支持多用户声纹注册和识别
"""
import os
import json
import numpy as np
from typing import Dict, List, Optional, Any
from pathlib import Path

from app.utils.logger import logger


class VoiceprintRecognizer:
    """
    声纹识别器
    
    支持：
    - 声纹注册
    - 声纹识别
    - 声纹管理
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._voiceprints: Dict[str, np.ndarray] = {}
            cls._instance._voiceprint_dir = "data/voiceprints"
            cls._instance._model = None
        return cls._instance
    
    def __init__(self):
        # 确保目录存在
        os.makedirs(self._voiceprint_dir, exist_ok=True)
        
        # 加载已有的声纹
        self._load_voiceprints()
        
        logger.info(f"[Voiceprint] 初始化完成，已注册声纹: {len(self._voiceprints)} 个")
    
    def _load_model(self):
        """加载声纹识别模型"""
        try:
            # 尝试加载 3D-Speaker 模型
            # 这里可以集成实际的声纹识别模型
            logger.info("[Voiceprint] 声纹识别模型加载完成")
            self._model = True
        except Exception as e:
            logger.error(f"[Voiceprint] 模型加载失败: {e}")
            self._model = None
    
    def _load_voiceprints(self):
        """从文件加载已注册的声纹"""
        voiceprint_file = Path(self._voiceprint_dir) / "voiceprints.json"
        
        if voiceprint_file.exists():
            try:
                with open(voiceprint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for user_id, embedding_list in data.items():
                        self._voiceprints[user_id] = np.array(embedding_list)
                logger.info(f"[Voiceprint] 加载声纹: {len(self._voiceprints)} 个")
            except Exception as e:
                logger.error(f"[Voiceprint] 加载声纹失败: {e}")
    
    def _save_voiceprints(self):
        """保存声纹到文件"""
        voiceprint_file = Path(self._voiceprint_dir) / "voiceprints.json"
        
        try:
            data = {}
            for user_id, embedding in self._voiceprints.items():
                data[user_id] = embedding.tolist()
            
            with open(voiceprint_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            
            logger.info(f"[Voiceprint] 保存声纹: {len(self._voiceprints)} 个")
        except Exception as e:
            logger.error(f"[Voiceprint] 保存声纹失败: {e}")
    
    async def register(self, user_id: str, audio_data: np.ndarray) -> bool:
        """
        注册声纹
        
        Args:
            user_id: 用户 ID
            audio_data: 音频数据（用于提取声纹特征）
            
        Returns:
            是否注册成功
        """
        try:
            # 提取声纹特征（这里使用简化的特征提取）
            # 实际项目中应该使用专业的声纹识别模型
            embedding = self._extract_embedding(audio_data)
            
            if embedding is None:
                logger.error("[Voiceprint] 声纹特征提取失败")
                return False
            
            # 保存声纹
            self._voiceprints[user_id] = embedding
            self._save_voiceprints()
            
            logger.info(f"[Voiceprint] 声纹注册成功: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[Voiceprint] 声纹注册失败: {e}")
            return False
    
    async def recognize(self, audio_data: np.ndarray, threshold: float = 0.8) -> Optional[str]:
        """
        识别声纹
        
        Args:
            audio_data: 音频数据
            threshold: 相似度阈值
            
        Returns:
            识别到的用户 ID，或 None
        """
        if not self._voiceprints:
            logger.warning("[Voiceprint] 无已注册声纹")
            return None
        
        try:
            # 提取声纹特征
            embedding = self._extract_embedding(audio_data)
            
            if embedding is None:
                return None
            
            # 计算与所有已注册声纹的相似度
            best_match = None
            best_score = 0
            
            for user_id, registered_embedding in self._voiceprints.items():
                score = self._cosine_similarity(embedding, registered_embedding)
                
                if score > best_score:
                    best_score = score
                    best_match = user_id
            
            # 检查是否超过阈值
            if best_score >= threshold:
                logger.info(f"[Voiceprint] 识别成功: {best_match} (相似度: {best_score:.2f})")
                return best_match
            else:
                logger.info(f"[Voiceprint] 识别失败: 最高相似度 {best_score:.2f} < {threshold}")
                return None
                
        except Exception as e:
            logger.error(f"[Voiceprint] 声纹识别失败: {e}")
            return None
    
    def _extract_embedding(self, audio_data: np.ndarray) -> Optional[np.ndarray]:
        """
        从音频数据中提取声纹特征
        
        Args:
            audio_data: 音频数据
            
        Returns:
            声纹特征向量
        """
        try:
            # 简化的特征提取（实际项目中应使用专业模型）
            # 这里使用音频的统计特征作为示例
            if len(audio_data) == 0:
                return None
            
            # 计算音频特征
            embedding = np.array([
                np.mean(audio_data),
                np.std(audio_data),
                np.max(audio_data),
                np.min(audio_data),
                len(audio_data)
            ])
            
            # 归一化
            norm = np.linalg.norm(embedding)
            if norm > 0:
                embedding = embedding / norm
            
            return embedding
            
        except Exception as e:
            logger.error(f"[Voiceprint] 特征提取失败: {e}")
            return None
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def delete_voiceprint(self, user_id: str) -> bool:
        """删除声纹"""
        if user_id in self._voiceprints:
            del self._voiceprints[user_id]
            self._save_voiceprints()
            logger.info(f"[Voiceprint] 删除声纹: {user_id}")
            return True
        return False
    
    def list_voiceprints(self) -> List[str]:
        """列出所有已注册的声纹"""
        return list(self._voiceprints.keys())
    
    def get_status(self) -> Dict[str, Any]:
        """获取声纹识别状态"""
        return {
            "registered_count": len(self._voiceprints),
            "users": list(self._voiceprints.keys())
        }


# 全局声纹识别器实例
voiceprint_recognizer = VoiceprintRecognizer()
