import os
from celery import Celery
from app.core.config import get_settings as settings

REDIS_URL = settings().redis_url



celery_app = Celery(
    "worker",
    broker=f"{REDIS_URL}/0",
    backend=f"{REDIS_URL}/1",
    include=["worker.tasks"],
)
celery_app.conf.update(
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,
    broker_connection_retry_on_startup=True,
)