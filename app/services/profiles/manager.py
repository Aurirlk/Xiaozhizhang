"""
人物画像管理器
使用 JSON 文件保存用户画像
"""
import os
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from app.utils.logger import logger


class ProfileManager:
    """
    人物画像管理器
    
    功能：
    - 保存用户画像到 JSON 文件
    - 加载用户画像
    - 合并用户画像
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._profiles_dir = "data/profiles"
        return cls._instance
    
    def __init__(self):
        # 确保目录存在
        os.makedirs(self._profiles_dir, exist_ok=True)
        logger.info(f"[Profile] 人物画像管理器初始化完成，目录: {self._profiles_dir}")
    
    async def save_profile(
        self, 
        user_id: str, 
        profile_data: Dict[str, Any]
    ) -> bool:
        """
        保存用户画像
        
        Args:
            user_id: 用户 ID
            profile_data: 画像数据
            
        Returns:
            是否保存成功
        """
        try:
            # 加载现有画像
            existing = await self.load_profile(user_id)
            
            if existing:
                # 合并数据
                merged = self._merge_profile(existing, profile_data)
                merged["updated_at"] = datetime.now().isoformat()
            else:
                merged = {
                    "user_id": user_id,
                    "profile": profile_data,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            
            file_path = os.path.join(self._profiles_dir, f"{user_id}.json")
            
            async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
                await f.write(json.dumps(merged, ensure_ascii=False, indent=2))
            
            logger.info(f"[Profile] 保存画像: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"[Profile] 保存画像失败: {e}")
            return False
    
    async def load_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        加载用户画像
        
        Args:
            user_id: 用户 ID
            
        Returns:
            画像数据
        """
        file_path = os.path.join(self._profiles_dir, f"{user_id}.json")
        
        if not os.path.exists(file_path):
            return None
        
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"[Profile] 加载画像失败: {e}")
            return None
    
    async def update_profile(
        self, 
        user_id: str, 
        profile_data: Dict[str, Any]
    ) -> bool:
        """
        更新用户画像
        
        Args:
            user_id: 用户 ID
            profile_data: 新的画像数据
            
        Returns:
            是否更新成功
        """
        return await self.save_profile(user_id, profile_data)
    
    def _merge_profile(
        self, 
        existing: Dict[str, Any], 
        new_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        合并用户画像
        
        Args:
            existing: 现有画像
            new_data: 新数据
            
        Returns:
            合并后的画像
        """
        profile = existing.get("profile", {})
        
        # 合并基本字段
        for key in ["name", "gender", "age_range", "occupation", "city", 
                     "intent", "budget_range", "notes"]:
            if key in new_data and new_data[key]:
                profile[key] = new_data[key]
        
        # 合并偏好信息
        if "preferences" in new_data and new_data["preferences"]:
            if "preferences" not in profile:
                profile["preferences"] = {}
            for k, v in new_data["preferences"].items():
                if v:
                    if k in profile["preferences"]:
                        existing = profile["preferences"][k] or []
                        profile["preferences"][k] = list(set(existing + v))
                    else:
                        profile["preferences"][k] = v
        
        # 合并标签
        if "tags" in new_data and new_data["tags"]:
            if "tags" not in profile:
                profile["tags"] = []
            profile["tags"] = list(set(profile["tags"] + new_data["tags"]))
        
        existing["profile"] = profile
        return existing
    
    async def get_all_profiles(self) -> List[Dict[str, Any]]:
        """获取所有用户画像"""
        profiles = []
        
        for file_name in os.listdir(self._profiles_dir):
            if file_name.endswith(".json"):
                file_path = os.path.join(self._profiles_dir, file_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        profiles.append(data)
                except Exception as e:
                    logger.error(f"[Profile] 读取画像失败: {file_name}, {e}")
        
        return profiles
    
    async def delete_profile(self, user_id: str) -> bool:
        """删除用户画像"""
        file_path = os.path.join(self._profiles_dir, f"{user_id}.json")
        
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"[Profile] 删除画像: {user_id}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取画像统计"""
        files = [f for f in os.listdir(self._profiles_dir) if f.endswith(".json")]
        return {
            "total_profiles": len(files),
            "directory": self._profiles_dir
        }


# 全局人物画像管理器实例
profile_manager = ProfileManager()
