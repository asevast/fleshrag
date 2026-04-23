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
    task_default_retry_delay=30,  # секунд между ретраями
    task_max_retries=3,
)


@worker_ready.connect
def at_start(sender, **k):
    from app.config import settings
    for path in settings.index_paths.split(":"):
        if os.path.isdir(path):
            index_directory_task.delay(path)


@celery_app.task(bind=True, max_retries=3)
def index_directory_task(self, path: str):
    from app.indexer.watcher import index_directory
    from app.models.router import ModelRouter
    try:
        router = ModelRouter()
        index_directory(path, router=router)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3)
def index_file_task(self, file_path: str):
    from app.indexer.watcher import index_single_file
    from app.models.router import ModelRouter
    try:
        router = ModelRouter()
        index_single_file(file_path, router=router)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=10)
