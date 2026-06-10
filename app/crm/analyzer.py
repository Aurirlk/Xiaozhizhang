"""
CRM 分析模块
利用 LLM 从对话中提取用户信息并存入数据库
"""
import json
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crm_models import User, Interaction, UserProfile
from app.services.factory import ServiceFactory
from app.config import settings


# CRM 信息提取 Prompt
CRM_EXTRACTION_PROMPT = """你是一个专业的用户信息分析助手。请从以下对话内容中提取用户的特征信息。

对话内容：
{conversation}

请以 JSON 格式返回提取到的信息，包含以下字段（如果对话中没有提到相关信息，对应字段设为 null）：

{{
    "name": "用户姓名",
    "gender": "性别（男/女）",
    "age_range": "年龄段（如：20-30岁、中年、老年等）",
    "occupation": "职业",
    "city": "所在城市",
    "preferences": {{
        "hobbies": ["爱好列表"],
        "food": ["饮食偏好"],
        "music": ["音乐偏好"],
        "other": ["其他偏好"]
    }},
    "intent": "用户意向（如：购买、咨询、投诉等）",
    "budget_range": "预算范围",
    "tags": ["用户标签，如：高意向、价格敏感等"],
    "notes": "其他值得注意的信息"
}}

注意：
1. 只提取明确提到的信息，不要推测
2. 如果某个字段不确定，设为 null
3. 返回纯 JSON 格式，不要包含其他文字
"""

# 意图分类 Prompt
INTENT_EXTRACTION_PROMPT = """你是一个意图分析助手。请分析以下对话，识别用户的意图。

对话内容：
{conversation}

请返回 JSON 格式的分析结果：
{{
    "intent": "意图类型",
    "confidence": 0.95,
    "entities": {{"key": "value"}}
}}

意图类型包括：
- weather: 查询天气（包含天气、温度、下雨等关键词）
- news: 获取新闻（包含新闻、热点、大瓜等关键词）
- search: 搜索信息（包含搜索、查一下、是什么等关键词）
- knowledge: 查询知识库（包含知识库、专业、领域等关键词）
- chat: 闲聊对话（其他所有情况）

entities 中可能包含：
- weather: {{"city": "城市名"}}
- news: {{"category": "类别"}}
- search: {{"query": "搜索词"}}
- knowledge: {{"topic": "主题"}}

返回纯 JSON 格式，不要包含其他文字。
"""


class CRMAnalyzer:
    """CRM 分析服务"""
    
    def __init__(self):
        self.llm_service = None
        
    def _get_llm(self):
        """懒加载 LLM 服务"""
        if self.llm_service is None:
            self.llm_service = ServiceFactory.create_llm()
        return self.llm_service
    
    async def extract_user_info(self, conversation: str) -> Dict[str, Any]:
        """
        从对话中提取用户信息
        
        Args:
            conversation: 对话内容
            
        Returns:
            提取到的用户信息字典
        """
        try:
            prompt = CRM_EXTRACTION_PROMPT.format(conversation=conversation)
            llm = self._get_llm()
            
            response = await llm.chat(prompt)
            
            # 清理响应，提取 JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # 解析 JSON
            user_info = json.loads(response)
            return user_info
            
        except json.JSONDecodeError as e:
            print(f"[CRM] JSON 解析失败: {e}")
            return {}
        except Exception as e:
            print(f"[CRM] 信息提取失败: {e}")
            return {}
    
    async def extract_intent(self, user_message: str) -> Dict[str, Any]:
        """
        从用户消息中提取意图
        
        Args:
            user_message: 用户消息
            
        Returns:
            提取到的意图信息字典
        """
        try:
            prompt = INTENT_EXTRACTION_PROMPT.format(conversation=user_message)
            llm = self._get_llm()
            
            response = await llm.chat(prompt)
            
            # 清理响应，提取 JSON
            response = response.strip()
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
            # 解析 JSON
            intent_info = json.loads(response)
            return intent_info
            
        except json.JSONDecodeError as e:
            print(f"[CRM] 意图 JSON 解析失败: {e}")
            return {"intent": "chat", "confidence": 0.5, "entities": {}}
        except Exception as e:
            print(f"[CRM] 意图提取失败: {e}")
            return {"intent": "chat", "confidence": 0.5, "entities": {}}
    
    async def analyze_and_save(
        self, 
        db: AsyncSession, 
        interaction_id: str,
        user_id: str,
        conversation: str
    ) -> Optional[UserProfile]:
        """
        分析对话并保存用户画像
        
        Args:
            db: 数据库会话
            interaction_id: 交互记录 ID
            user_id: 用户 ID
            conversation: 对话内容
            
        Returns:
            更新后的用户画像
        """
        # 提取用户信息
        user_info = await self.extract_user_info(conversation)
        
        if not user_info:
            return None
        
        # 更新交互记录
        result = await db.execute(
            select(Interaction).where(Interaction.id == interaction_id)
        )
        interaction = result.scalar_one_or_none()
        
        if interaction:
            interaction.crm_analyzed = True
            interaction.crm_extracted_data = user_info
            
            # 提取意图并保存
            intent_info = await self.extract_user_info(conversation)
            if intent_info.get("intent"):
                interaction.intent = intent_info.get("intent")
                interaction.intent_confidence = int(intent_info.get("confidence", 0.5) * 100)
                interaction.intent_source = "llm"
                interaction.entities = intent_info.get("entities")
        
        # 获取或创建用户画像
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        profile = result.scalar_one_or_none()
        
        if profile is None:
            profile = UserProfile(user_id=user_id)
            db.add(profile)
        
        # 更新用户画像（合并现有数据）
        profile = self._merge_profile(profile, user_info)
        
        await db.commit()
        return profile
    
    def _merge_profile(self, profile: UserProfile, new_data: Dict[str, Any]) -> UserProfile:
        """
        合并用户画像数据
        
        Args:
            profile: 现有用户画像
            new_data: 新提取的数据
            
        Returns:
            更新后的用户画像
        """
        # 更新基本字段（只在新数据不为空时更新）
        if new_data.get("name"):
            profile.name = new_data["name"]
        if new_data.get("gender"):
            profile.gender = new_data["gender"]
        if new_data.get("age_range"):
            profile.age_range = new_data["age_range"]
        if new_data.get("occupation"):
            profile.occupation = new_data["occupation"]
        if new_data.get("city"):
            profile.city = new_data["city"]
        if new_data.get("intent"):
            profile.intent = new_data["intent"]
        if new_data.get("budget_range"):
            profile.budget_range = new_data["budget_range"]
        if new_data.get("notes"):
            profile.notes = new_data["notes"]
        
        # 合并偏好信息
        if new_data.get("preferences"):
            if profile.preferences is None:
                profile.preferences = {}
            for key, value in new_data["preferences"].items():
                if value:
                    if key in profile.preferences:
                        # 合并列表，去重
                        existing = profile.preferences[key] or []
                        profile.preferences[key] = list(set(existing + value))
                    else:
                        profile.preferences[key] = value
        
        # 合并标签
        if new_data.get("tags"):
            if profile.tags is None:
                profile.tags = []
            profile.tags = list(set(profile.tags + new_data["tags"]))
        
        profile.updated_at = datetime.utcnow()
        return profile


# 全局 CRM 分析器实例
crm_analyzer = CRMAnalyzer()


async def analyze_interaction_background(
    interaction_id: str,
    user_id: str,
    user_message: str,
    assistant_message: str
):
    """
    后台异步分析交互记录
    
    Args:
        interaction_id: 交互记录 ID
        user_id: 用户 ID
        user_message: 用户消息
        assistant_message: 助手回复
    """
    from app.database import async_session_factory
    
    conversation = f"用户：{user_message}\n助手：{assistant_message}"
    
    try:
        async with async_session_factory() as db:
            await crm_analyzer.analyze_and_save(
                db=db,
                interaction_id=interaction_id,
                user_id=user_id,
                conversation=conversation
            )
            print(f"[CRM] 交互记录 {interaction_id} 分析完成")
    except Exception as e:
        print(f"[CRM] 后台分析失败: {e}")
