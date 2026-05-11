"""
知识库查询工具
基于 Coze 工作流的 Function Calling 工具
"""
import json
from typing import Any, Dict

from app.tools.base import BaseTool, ToolResult
from app.utils.logger import logger


class KnowledgeTool(BaseTool):
    """知识库查询工具"""
    
    @property
    def name(self) -> str:
        return "query_knowledge"
    
    @property
    def description(self) -> str:
        return "查询知识库获取专业信息。当用户询问专业领域知识、技术问题、或需要从本地知识库检索信息时调用此工具。"
    
    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "查询内容，例如：'什么是机器学习'、'Python如何实现多线程'"
                        },
                        "context": {
                            "type": "string",
                            "description": "可选的上下文信息，帮助更精确地检索"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    
    async def execute(self, **kwargs) -> ToolResult:
        """执行知识库查询"""
        query = kwargs.get("query", "")
        context = kwargs.get("context", "")
        
        if not query:
            return ToolResult(
                success=False,
                data=None,
                error="查询内容不能为空",
                tool_name=self.name
            )
        
        try:
            # 尝试使用 Coze 工作流
            from app.services.coze.coze_client import CozeClient
            
            coze_client = CozeClient()
            result = await coze_client.query_knowledge(query, context)
            
            return ToolResult(
                success=True,
                data=result,
                tool_name=self.name
            )
            
        except ImportError:
            # Coze 客户端未实现，降级到本地知识库查询
            logger.warning("[KnowledgeTool] Coze 客户端未实现，尝试本地查询")
            return await self._local_query(query, context)
        except Exception as e:
            logger.error(f"[KnowledgeTool] 执行失败: {e}")
            return ToolResult(
                success=False,
                data=None,
                error=str(e),
                tool_name=self.name
            )
    
    async def _local_query(self, query: str, context: str = "") -> ToolResult:
        """
        本地知识库查询（使用 RAG 服务）
        """
        try:
            from app.knowledge.rag_service import rag_service
            
            # 加载知识库（如果未加载）
            await rag_service.load_knowledge_base()
            
            # 搜索相关文档
            search_results = await rag_service.search(query, limit=3)
            
            if search_results:
                # 拼接上下文
                context_parts = []
                for result in search_results:
                    source = result.get("source", "未知")
                    content = result.get("content", "")
                    context_parts.append(f"[来源: {source}]\n{content}")
                
                knowledge_context = "\n\n".join(context_parts)
                
                # 让 LLM 基于知识库内容回答
                from app.services.factory import ServiceFactory
                llm_service = ServiceFactory.create_llm()
                
                prompt = f"""基于以下知识库内容回答用户问题。

知识库内容：
{knowledge_context}

用户问题：{query}

请基于知识库内容准确回答。如果知识库中没有相关信息，请说明。"""
                
                reply = await llm_service.chat(prompt)
                
                return ToolResult(
                    success=True,
                    data={
                        "response": reply, 
                        "source": "knowledge_base",
                        "search_results": search_results
                    },
                    tool_name=self.name
                )
            else:
                # 知识库中没有找到相关内容，降级到 LLM 直接回答
                from app.services.factory import ServiceFactory
                llm_service = ServiceFactory.create_llm()
                prompt = f"请根据你的知识回答以下问题：{query}"
                reply = await llm_service.chat(prompt)
                
                return ToolResult(
                    success=True,
                    data={"response": reply, "source": "llm_fallback"},
                    tool_name=self.name
                )
                
        except Exception as e:
            return ToolResult(
                success=False,
                data=None,
                error=f"知识库查询失败: {str(e)}",
                tool_name=self.name
            )
