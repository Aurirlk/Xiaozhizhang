"""
意图分类器
支持 LLM 意图识别 + 关键词兜底
"""
import json
import re
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

from app.utils.logger import logger


class IntentType(str, Enum):
    """意图类型枚举"""
    WEATHER = "weather"           # 天气查询
    NEWS = "news"                 # 新闻获取
    SEARCH = "search"             # 联网搜索
    KNOWLEDGE = "knowledge"       # 法律/专业知识库
    TIME = "time"                 # 时间查询（直接走 LLM，system prompt 已注入时间）
    CHAT = "chat"                 # 闲聊对话
    UNKNOWN = "unknown"           # 未知意图


@dataclass
class IntentResult:
    """意图分类结果"""
    intent: IntentType
    confidence: float  # 置信度 0-1
    entities: Dict[str, Any]  # 提取的实体（如城市名、搜索词等）
    raw_text: str  # 原始文本
    source: str  # 分类来源: "llm" 或 "keyword"


class IntentClassifier:
    """
    意图分类器
    
    分类策略：
    1. 关键词匹配（快速、确定性）
    2. LLM 意图识别（兜底、处理复杂情况）
    """
    
    # 关键词规则库
    KEYWORD_RULES = {
        IntentType.WEATHER: {
            "keywords": ["天气", "气温", "温度", "下雨", "晴天", "多云", "刮风", 
                        "降温", "升温", "湿度", "紫外线", "空气质量"],
            "patterns": [
                r"(?P<city>.+?)的?(?:今天|明天|后天|现在)?天气",  # "江西南昌的今天天气"
                r"(?P<city>.+?)的?天气",                         # "北京天气"
                r"(?P<city>.+?)多少度",                          # "北京多少度"
                r"(?P<city>.+?)会不会下雨",                      # "明天会不会下雨"
            ]
        },
        IntentType.NEWS: {
            "keywords": ["新闻", "大瓜", "热点", "最新消息", "发生了什么", 
                        "今日要闻", "头条", "时事"],
            "patterns": [
                r"(社会|财经|国际|军事|娱乐|体育)新闻",
                r"播报.*新闻",
                r"有什么.*新闻",
            ]
        },
        IntentType.SEARCH: {
            "keywords": ["搜索", "查一下", "查询", "是什么", "什么是", "怎么",
                        "如何", "为什么", "哪里", "在哪", "帮我查", "上网查"],
            "patterns": [
                r"帮我查",
                r"搜索一下",
                r"上网查",
                r"查一下.*",
            ]
        },
        IntentType.KNOWLEDGE: {
            "keywords": ["法律", "法规", "法条", "规定", "条例", "合同", "劳动法",
                        "民法典", "刑法", "治安", "处罚", "权利", "义务", "诉讼",
                        "律师", "法院", "判决", "合同法", "知识产权"],
            "patterns": [
                r"根据.*法",
                r".*法.*规定",
                r"法律.*问题",
                r"合同.*纠纷",
                r"劳动.*争议",
            ]
        },
        IntentType.TIME: {
            "keywords": ["时间", "几点", "日期", "今天", "明天", "昨天", "星期", 
                        "几号", "什么时候", "现在", "当前"],
            "patterns": [
                r"现在几点",
                r"今天几号",
                r"今天星期几",
                r"现在.*时间",
                r"当前.*时间",
            ]
        },
    }
    
    # LLM 意图识别提示词
    INTENT_PROMPT = """你是一个意图分类助手。根据用户输入，判断用户的意图类型。

可选的意图类型：
- weather: 查询天气（包含天气、温度、下雨等关键词）
- news: 获取新闻（包含新闻、热点、大瓜等关键词）
- search: 搜索信息（包含搜索、查一下、是什么等关键词）
- knowledge: 查询知识库（包含知识库、专业、领域等关键词）
- chat: 闲聊对话（其他所有情况）

用户输入：{user_input}

请返回 JSON 格式的分类结果：
{{
    "intent": "意图类型",
    "confidence": 0.95,
    "entities": {{"key": "value"}}
}}

entities 中可能包含：
- weather: {{"city": "城市名"}}
- news: {{"category": "类别"}}
- search: {{"query": "搜索词"}}
- knowledge: {{"topic": "主题"}}
"""
    
    def __init__(self):
        """初始化意图分类器"""
        pass
    
    async def classify(self, user_input: str) -> IntentResult:
        """
        对用户输入进行意图分类
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            IntentResult 分类结果
        """
        # 1. 先尝试关键词匹配（快速、确定性）
        keyword_result = self._keyword_classify(user_input)
        if keyword_result and keyword_result.confidence >= 0.8:
            logger.info(f"[Intent] 关键词匹配: {keyword_result.intent.value} (置信度: {keyword_result.confidence})")
            return keyword_result
        
        # 2. 关键词匹配失败或置信度低，使用 LLM 分类
        llm_result = await self._llm_classify(user_input)
        if llm_result:
            logger.info(f"[Intent] LLM 分类: {llm_result.intent.value} (置信度: {llm_result.confidence})")
            return llm_result
        
        # 3. LLM 也失败，返回默认聊天意图
        logger.info("[Intent] 默认分类: chat")
        return IntentResult(
            intent=IntentType.CHAT,
            confidence=0.5,
            entities={},
            raw_text=user_input,
            source="default"
        )
    
    def _keyword_classify(self, user_input: str) -> Optional[IntentResult]:
        """
        基于关键词的意图分类
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            IntentResult 或 None
        """
        user_input_lower = user_input.lower()
        
        best_intent = None
        best_score = 0
        best_entities = {}
        
        for intent_type, rules in self.KEYWORD_RULES.items():
            score = 0
            entities = {}
            
            # 检查关键词
            for keyword in rules["keywords"]:
                if keyword in user_input_lower:
                    score += 1
            
            # 检查正则表达式
            for pattern in rules.get("patterns", []):
                match = re.search(pattern, user_input)
                if match:
                    score += 2  # 正则匹配权重更高
                    # 提取命名组
                    entities.update(match.groupdict())
            
            # 计算置信度
            if score > 0:
                confidence = min(score / 3.0, 1.0)  # 归一化到 0-1
                
                if confidence > best_score:
                    best_score = confidence
                    best_intent = intent_type
                    best_entities = entities
        
        if best_intent:
            return IntentResult(
                intent=best_intent,
                confidence=best_score,
                entities=best_entities,
                raw_text=user_input,
                source="keyword"
            )
        
        return None
    
    async def _llm_classify(self, user_input: str) -> Optional[IntentResult]:
        """
        基于 LLM 的意图分类
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            IntentResult 或 None
        """
        try:
            from app.services.factory import ServiceFactory
            
            llm_service = ServiceFactory.create_llm()
            
            prompt = self.INTENT_PROMPT.format(user_input=user_input)
            response = await llm_service.chat(prompt)
            
            # 解析 JSON 响应
            # 尝试提取 JSON 部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())
                
                intent_str = result.get("intent", "chat").lower()
                confidence = result.get("confidence", 0.7)
                entities = result.get("entities", {})
                
                # 映射到 IntentType
                try:
                    intent = IntentType(intent_str)
                except ValueError:
                    intent = IntentType.CHAT
                
                return IntentResult(
                    intent=intent,
                    confidence=confidence,
                    entities=entities,
                    raw_text=user_input,
                    source="llm"
                )
                
        except Exception as e:
            logger.error(f"[Intent] LLM 分类失败: {e}")
        
        return None
    
    def add_keyword_rule(self, intent: IntentType, keywords: list, patterns: list = None):
        """
        动态添加关键词规则
        
        Args:
            intent: 意图类型
            keywords: 关键词列表
            patterns: 正则表达式列表
        """
        if intent not in self.KEYWORD_RULES:
            self.KEYWORD_RULES[intent] = {"keywords": [], "patterns": []}
        
        self.KEYWORD_RULES[intent]["keywords"].extend(keywords)
        if patterns:
            self.KEYWORD_RULES[intent]["patterns"].extend(patterns)
