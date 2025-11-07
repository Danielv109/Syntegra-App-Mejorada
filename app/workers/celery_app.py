from celery import Celery
from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "syntegra_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.workers.etl_tasks",
        "app.workers.analysis_tasks",
        "app.workers.report_tasks",
    ]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hora
    task_soft_time_limit=3300,  # 55 minutos
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,  # 1 minuto
    task_max_retries=3,
)
