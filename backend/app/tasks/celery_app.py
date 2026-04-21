import os
from celery import Celery
from celery.signals import worker_ready

from app.config import settings

redis_url = settings.redis_url

celery_app = Celery("multimodal_rag", broker=redis_url, backend=redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@worker_ready.connect
def at_start(sender, **k):
    from app.config import settings
    for path in settings.index_paths.split(":"):
        if os.path.isdir(path):
            index_directory_task.delay(path)


@celery_app.task
def index_directory_task(path: str):
    from app.indexer.watcher import index_directory
    index_directory(path)


@celery_app.task
def index_file_task(file_path: str):
    from app.indexer.watcher import index_single_file
    index_single_file(file_path)
