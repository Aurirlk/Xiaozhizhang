"""任务队列模块"""
from app.tasks.celery_app import celery_app
from app.tasks.crm_tasks import analyze_interaction_task, process_audio_task

__all__ = ["celery_app", "analyze_interaction_task", "process_audio_task"]
