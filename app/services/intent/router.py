"""
意图路由器
根据意图分类结果分发到对应的处理函数
"""
import json
from typing import Callable, Dict, Any, Optional, List

from app.services.intent.classifier import IntentClassifier, IntentType, IntentResult
from app.services.factory import ServiceFactory
from app.services.emotion.analyzer import emotion_analyzer, EmotionType
from app.tools.registry import tool_registry
from app.tools.base import ToolResult
from app.utils.logger import logger


class IntentRouter:
    """
    意图路由器
    
    根据意图类型分发到对应的处理器：
    - weather → 天气查询工具
    - news → 新闻获取工具
    - search → 网页搜索工具
    - knowledge → 知识库查询工具
    - chat → 直接对话
    
    支持情感分析和情绪 TTS
    """
    
    def __init__(self):
        self.classifier = IntentClassifier()
        self._handlers: Dict[IntentType, Callable] = {}
        self._history_getter: Optional[Callable] = None
        
        # 意图到工具的映射
        self._intent_tool_map = {
            IntentType.WEATHER: "get_weather",
            IntentType.NEWS: "get_trending_news",
            IntentType.SEARCH: "web_search",
            IntentType.KNOWLEDGE: "query_knowledge",
        }
        
        # 注册默认处理器
        self._register_default_handlers()
    
    def set_history_getter(self, getter: Callable):
        """
        设置历史获取函数
        
        Args:
            getter: 接收 session_id，返回历史列表的函数
        """
        self._history_getter = getter
    
    def _register_default_handlers(self):
        """注册默认的意图处理器"""
        # Function Calling 分支（天气/新闻/搜索/知识库）
        self._handlers[IntentType.WEATHER] = self._handle_tool_with_llm
        self._handlers[IntentType.NEWS] = self._handle_tool_with_llm
        self._handlers[IntentType.SEARCH] = self._handle_tool_with_llm
        self._handlers[IntentType.KNOWLEDGE] = self._handle_tool_with_llm
        # 时间查询直接走 LLM（system prompt 已注入当前时间）
        self._handlers[IntentType.TIME] = self._handle_chat
        # 直接 LLM 对话分支（闲聊）
        self._handlers[IntentType.CHAT] = self._handle_chat
        self._handlers[IntentType.UNKNOWN] = self._handle_chat
    
    def register_handler(self, intent: IntentType, handler: Callable):
        """
        注册自定义意图处理器
        
        Args:
            intent: 意图类型
            handler: 处理函数
        """
        self._handlers[intent] = handler
    
    def _get_history(self, session_id: str) -> List[Dict[str, str]]:
        """获取会话历史"""
        if self._history_getter and session_id:
            return self._history_getter(session_id)
        return []
    
    async def route(self, user_input: str, session_id: str = None) -> Dict[str, Any]:
        """
        路由用户输入到对应的处理器
        
        Args:
            user_input: 用户输入文本
            session_id: 会话 ID
            
        Returns:
            处理结果字典
        """
        # 1. 意图分类
        intent_result = await self.classifier.classify(user_input)
        
        logger.info(f"[Router] 意图: {intent_result.intent.value}, "
                    f"置信度: {intent_result.confidence:.2f}, "
                    f"来源: {intent_result.source}")
        
        # 2. 获取对应的处理器
        handler = self._handlers.get(intent_result.intent, self._handle_chat)
        
        # 3. 执行处理
        try:
            result = await handler(user_input, intent_result, session_id)
            result["intent"] = intent_result.intent.value
            result["intent_confidence"] = intent_result.confidence
            result["intent_source"] = intent_result.source
            result["entities"] = intent_result.entities
            return result
        except Exception as e:
            logger.error(f"[Router] 处理失败: {e}")
            # 降级到聊天处理
            return await self._handle_chat(user_input, intent_result, session_id)
    
    async def _handle_tool_with_llm(
        self, 
        user_input: str, 
        intent_result: IntentResult,
        session_id: str = None
    ) -> Dict[str, Any]:
        """
        通用工具处理：执行工具 + LLM 生成回复
        
        流程：
        1. 从意图映射获取工具名称
        2. 从实体中提取工具参数
        3. 执行工具
        4. LLM 根据工具结果生成自然语言回复
        """
        tool_name = self._intent_tool_map.get(intent_result.intent)
        
        if not tool_name:
            return await self._handle_chat(user_input, intent_result, session_id)
        
        # 执行工具
        tool_result = await tool_registry.execute_tool(
            tool_name, 
            **intent_result.entities
        )
        
        # 工具参数缺失时，用 LLM 从用户输入中提取
        if not tool_result.success and "参数无效" in (tool_result.error or ""):
            extracted = await self._extract_params_with_llm(user_input, tool_name)
            if extracted:
                tool_result = await tool_registry.execute_tool(tool_name, **extracted)
        
        if not tool_result.success:
            logger.warning(f"[Router] 工具执行失败: {tool_result.error}")
            # 工具失败，降级到直接对话
            return await self._handle_chat(user_input, intent_result, session_id)
        
        # LLM 根据工具结果生成回复
        llm_service = ServiceFactory.create_llm()
        history = self._get_history(session_id)
        
        # 构建提示词
        tool_data = tool_result.data
        prompt = self._build_tool_prompt(user_input, tool_name, tool_data)
        
        reply = await llm_service.chat(prompt, history)
        
        return {
            "reply": reply,
            "tool_result": tool_data,
            "tool_name": tool_name
        }
    
    def _build_tool_prompt(self, user_input: str, tool_name: str, tool_data: Any) -> str:
        """构建工具结果提示词"""
        tool_data_str = json.dumps(tool_data, ensure_ascii=False, indent=2)
        
        prompts = {
            "get_weather": f"用户询问天气。天气数据如下：\n{tool_data_str}\n\n请用自然口语化的方式回答。",
            "get_trending_news": f"用户想看新闻。新闻数据如下：\n{tool_data_str}\n\n请用自然口语化的方式播报新闻。",
            "web_search": f"用户搜索：{user_input}\n搜索结果如下：\n{tool_data_str}\n\n请用自然口语化的方式回答。",
            "query_knowledge": f"用户查询知识库。查询结果如下：\n{tool_data_str}\n\n请用自然口语化的方式回答。",
        }
        
        return prompts.get(tool_name, f"工具结果：\n{tool_data_str}\n\n请回复用户。")
    
    async def _extract_params_with_llm(self, user_input: str, tool_name: str) -> Dict[str, Any]:
        """用 LLM 从用户输入中提取工具参数"""
        try:
            llm_service = ServiceFactory.create_llm()
            prompt = (
                f'用户说："{user_input}"\n'
                f'工具：{tool_name}\n'
                f'请从用户输入中提取工具所需的参数，返回 JSON 格式。'
                f'如果无法提取，返回空 JSON {{}}。\n'
                f'例如：用户说"北京天气"，返回 {{"city": "北京"}}'
            )
            reply = await llm_service.chat(prompt)
            import json
            # 尝试从回复中提取 JSON
            reply = reply.strip()
            if reply.startswith("```"):
                reply = reply.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            return json.loads(reply)
        except Exception:
            return {}

    async def _handle_chat(
        self, 
        user_input: str, 
        intent_result: IntentResult,
        session_id: str = None
    ) -> Dict[str, Any]:
        """处理闲聊对话（带历史上下文）"""
        llm_service = ServiceFactory.create_llm()
        history = self._get_history(session_id)
        reply = await llm_service.chat(user_input, history)
        
        return {
            "reply": reply,
            "tool_result": None,
            "tool_name": None
        }

