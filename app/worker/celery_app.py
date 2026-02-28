from celery import Celery
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Safety-net timeouts (per-stage timeouts are enforced in tasks.py)
    task_time_limit=300,          # hard kill after 5 min
    task_soft_time_limit=270,     # SoftTimeLimitExceeded after 4.5 min
)
