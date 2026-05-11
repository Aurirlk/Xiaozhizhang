"""
Coze 工作流 API 客户端
通过 HTTP API 调用 Coze 工作流
"""
import json
import os
from typing import Dict, Any, Optional

import httpx

from app.utils.logger import logger
from app.utils.config_loader import config_loader


class CozeClient:
    """
    Coze 工作流客户端
    
    通过 HTTP API 调用 Coze 工作流
    """
    
    def __init__(self):
        """初始化 Coze 客户端"""
        coze_config = config_loader.get_coze_config()
        
        self.api_key = coze_config.get("api_key") or os.getenv("COZE_API_KEY")
        self.base_url = coze_config.get("base_url", "https://api.coze.com")
        self.workflow_url = coze_config.get("workflow_url", f"{self.base_url}/v1/workflow/run")
        self.timeout = coze_config.get("timeout", 30)
        
        # 工作流配置
        self.workflows = coze_config.get("workflows", {})
        
        # 默认响应
        self.timeout_response = coze_config.get("response", {}).get(
            "timeout_response", "抱歉，知识库查询超时，请稍后再试。"
        )
        self.error_response = coze_config.get("response", {}).get(
            "error_response", "抱歉，知识库服务暂时不可用。"
        )
    
    async def query_knowledge(
        self, 
        query: str, 
        context: str = "",
        workflow_type: str = "knowledge_qa"
    ) -> Dict[str, Any]:
        """
        查询知识库（通过 Coze 工作流）
        
        Args:
            query: 查询内容
            context: 上下文信息
            workflow_type: 工作流类型
            
        Returns:
            查询结果
        """
        if not self.api_key:
            logger.warning("[Coze] API Key 未配置，降级到本地查询")
            return {"response": self.error_response, "source": "coze_error"}
        
        # 获取工作流 ID
        workflow_config = self.workflows.get(workflow_type, {})
        workflow_id = workflow_config.get("workflow_id")
        
        if not workflow_id:
            logger.warning(f"[Coze] 工作流 {workflow_type} 未配置")
            return {"response": self.error_response, "source": "coze_error"}
        
        try:
            # 构建请求参数
            payload = {
                "workflow_id": workflow_id,
                "parameters": {
                    "query": query,
                    "context": context
                }
            }
            
            # 发送请求
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.workflow_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
            
            if response.status_code != 200:
                logger.error(f"[Coze] API 调用失败: {response.status_code} - {response.text}")
                return {"response": self.error_response, "source": "coze_error"}
            
            result = response.json()
            
            # 解析响应
            output = result.get("output", {})
            response_text = output.get("response", "")
            
            if not response_text:
                response_text = output.get("text", self.error_response)
            
            return {
                "response": response_text,
                "source": "coze_workflow",
                "workflow_id": workflow_id,
                "raw_output": output
            }
            
        except httpx.TimeoutException:
            logger.error("[Coze] 请求超时")
            return {"response": self.timeout_response, "source": "coze_timeout"}
        except Exception as e:
            logger.error(f"[Coze] 请求失败: {e}")
            return {"response": self.error_response, "source": "coze_error"}
    
    async def run_workflow(
        self, 
        workflow_id: str, 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        运行指定的工作流
        
        Args:
            workflow_id: 工作流 ID
            parameters: 工作流参数
            
        Returns:
            工作流执行结果
        """
        if not self.api_key:
            return {"error": "API Key 未配置"}
        
        try:
            payload = {
                "workflow_id": workflow_id,
                "parameters": parameters
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    self.workflow_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
            
            if response.status_code != 200:
                return {"error": f"API 调用失败: {response.status_code}"}
            
            return response.json()
            
        except httpx.TimeoutException:
            return {"error": "请求超时"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}
    
    def get_available_workflows(self) -> Dict[str, str]:
        """获取可用的工作流列表"""
        return {
            name: config.get("workflow_id", "未配置")
            for name, config in self.workflows.items()
        }
