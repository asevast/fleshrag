from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.tasks.celery_app import index_directory_task

router = APIRouter()


class IndexPathRequest(BaseModel):
    path: str


@router.get("/index/status")
async def index_status():
    return {"status": "ok", "message": "Use celery flower or logs for detailed status"}


@router.post("/index/trigger")
async def trigger_index(background_tasks: BackgroundTasks):
    from app.config import settings
    for path in settings.index_paths.split(":"):
        index_directory_task.delay(path)
    return {"message": "Indexing triggered"}


@router.post("/index/add-path")
async def add_path(req: IndexPathRequest):
    index_directory_task.delay(req.path)
    return {"message": f"Indexing started for {req.path}"}
