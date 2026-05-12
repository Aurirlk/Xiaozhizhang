"""
CRM 分析任务
异步处理用户画像提取
"""
import asyncio
from app.tasks.celery_app import celery_app
from app.utils.logger import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def analyze_interaction_task(
    self,
    interaction_id: str,
    user_id: str,
    user_message: str,
    assistant_message: str
):
    """
    异步分析交互记录
    
    Args:
        interaction_id: 交互记录 ID
        user_id: 用户 ID
        user_message: 用户消息
        assistant_message: 助手回复
    """
    try:
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 运行异步任务
        loop.run_until_complete(
            _analyze_interaction(
                interaction_id, user_id, user_message, assistant_message
            )
        )
        
        loop.close()
        
        logger.info(f"[Task] 交互记录 {interaction_id} 分析完成")
        
    except Exception as e:
        logger.error(f"[Task] 分析失败: {e}")
        # 重试
        raise self.retry(exc=e, countdown=60)


async def _analyze_interaction(
    interaction_id: str,
    user_id: str,
    user_message: str,
    assistant_message: str
):
    """异步分析交互记录"""
    from app.database import async_session_factory
    from app.crm.analyzer import crm_analyzer
    
    conversation = f"用户：{user_message}\n助手：{assistant_message}"
    
    async with async_session_factory() as db:
        await crm_analyzer.analyze_and_save(
            db=db,
            interaction_id=interaction_id,
            user_id=user_id,
            conversation=conversation
        )


@celery_app.task(bind=True, max_retries=3)
def process_audio_task(self, audio_path: str, session_id: str):
    """
    异步处理音频任务
    
    Args:
        audio_path: 音频文件路径
        session_id: 会话 ID
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result = loop.run_until_complete(
            _process_audio(audio_path, session_id)
        )
        
        loop.close()
        return result
        
    except Exception as e:
        logger.error(f"[Task] 音频处理失败: {e}")
        raise self.retry(exc=e, countdown=30)


async def _process_audio(audio_path: str, session_id: str) -> dict:
    """异步处理音频"""
    from app.services.factory import ServiceFactory
    
    asr_service = ServiceFactory.create_asr()
    llm_service = ServiceFactory.create_llm()
    tts_service = ServiceFactory.create_tts()
    
    # ASR
    user_text = await asr_service.transcribe(audio_path)
    
    # LLM
    reply = await llm_service.chat(user_text)
    
    # TTS
    audio_path = await tts_service.synthesize(reply)
    
    return {
        "user_text": user_text,
        "reply": reply,
        "audio_path": audio_path
    }
