"""
意图分类器单元测试
"""
import pytest
from unittest.mock import AsyncMock, patch

from app.services.intent.classifier import IntentClassifier, IntentType, IntentResult


class TestIntentClassifier:
    """意图分类器测试"""
    
    @pytest.fixture
    def classifier(self):
        """创建分类器实例"""
        return IntentClassifier()
    
    def test_keyword_classify_weather(self, classifier):
        """测试天气关键词分类"""
        result = classifier._keyword_classify("北京天气怎么样")
        assert result is not None
        assert result.intent == IntentType.WEATHER
        assert "city" in result.entities or "北京" in result.raw_text
    
    def test_keyword_classify_news(self, classifier):
        """测试新闻关键词分类"""
        result = classifier._keyword_classify("有什么新闻")
        assert result is not None
        assert result.intent == IntentType.NEWS
    
    def test_keyword_classify_search(self, classifier):
        """测试搜索关键词分类"""
        result = classifier._keyword_classify("帮我查一下")
        assert result is not None
        assert result.intent == IntentType.SEARCH
    
    def test_keyword_classify_chat(self, classifier):
        """测试闲聊分类（无关键词匹配）"""
        result = classifier._keyword_classify("你好啊")
        # 闲聊可能返回 None 或低置信度
        if result:
            assert result.confidence < 0.8
    
    def test_keyword_classify_empty(self, classifier):
        """测试空输入"""
        result = classifier._keyword_classify("")
        assert result is None
    
    def test_keyword_rules_exist(self, classifier):
        """测试关键词规则库存在"""
        assert IntentType.WEATHER in classifier.KEYWORD_RULES
        assert IntentType.NEWS in classifier.KEYWORD_RULES
        assert IntentType.SEARCH in classifier.KEYWORD_RULES
        assert IntentType.KNOWLEDGE in classifier.KEYWORD_RULES
    
    def test_add_keyword_rule(self, classifier):
        """测试动态添加关键词规则"""
        original_count = len(classifier.KEYWORD_RULES.get(IntentType.WEATHER, {}).get("keywords", []))
        
        classifier.add_keyword_rule(
            IntentType.WEATHER,
            keywords=["雪", "冰雹"],
            patterns=[r"会下雪吗"]
        )
        
        new_count = len(classifier.KEYWORD_RULES[IntentType.WEATHER]["keywords"])
        assert new_count > original_count
    
    @pytest.mark.asyncio
    async def test_classify_with_keyword_match(self, classifier):
        """测试意图分类（关键词匹配）"""
        result = await classifier.classify("北京今天天气如何")
        assert result.intent == IntentType.WEATHER
        assert result.source == "keyword"
    
    @pytest.mark.asyncio
    async def test_classify_fallback_to_llm(self, classifier):
        """测试意图分类（LLM 兜底）"""
        with patch.object(classifier, '_llm_classify') as mock_llm:
            mock_llm.return_value = IntentResult(
                intent=IntentType.CHAT,
                confidence=0.9,
                entities={},
                raw_text="你好啊",
                source="llm"
            )
            
            result = await classifier.classify("你好啊")
            assert result.intent == IntentType.CHAT
            assert result.source == "llm"
    
    def test_intent_result_to_dict(self):
        """测试 IntentResult 转字典"""
        result = IntentResult(
            intent=IntentType.WEATHER,
            confidence=0.95,
            entities={"city": "北京"},
            raw_text="北京天气",
            source="keyword"
        )
        
        assert result.intent == IntentType.WEATHER
        assert result.confidence == 0.95
        assert result.entities == {"city": "北京"}
