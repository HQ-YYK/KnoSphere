from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# 初始化 Celery
celery_app = Celery(
    "knosphere_tasks",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
    include=["tasks.document_tasks", "tasks.embedding_tasks", "tasks.cleanup_tasks"]
)

# Celery 配置
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30分钟
    task_soft_time_limit=25 * 60,  # 25分钟
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
    task_routes={
        "tasks.document_tasks.*": {"queue": "documents"},
        "tasks.embedding_tasks.*": {"queue": "embeddings"},
        "tasks.cleanup_tasks.*": {"queue": "cleanup"},
    },
    task_annotations={
        "tasks.document_tasks.process_large_document": {"rate_limit": "10/m"},
        "*": {"max_retries": 3, "retry_backoff": True, "retry_backoff_max": 700, "retry_jitter": True},
    }
)

# 2026 年最佳实践：自动发现任务
celery_app.autodiscover_tasks(["tasks"])