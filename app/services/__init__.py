"""
服务模块
使用工厂模式创建和管理服务实例

使用示例:
    from app.services.factory import ServiceFactory
    
    # 自动选择（优先主选，失败回退备份）
    llm = ServiceFactory.create_llm()
    tts = ServiceFactory.create_tts()
    
    # 指定提供商
    llm = ServiceFactory.create_llm("deepseek")
    tts = ServiceFactory.create_tts("mimo")
"""

from app.services.factory import ServiceFactory, ServiceProvider, FallbackLLM, FallbackTTS

__all__ = [
    "ServiceFactory",
    "ServiceProvider", 
    "FallbackLLM",
    "FallbackTTS"
]
