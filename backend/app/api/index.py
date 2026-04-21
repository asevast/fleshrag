from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tasks.celery_app import index_directory_task
from app.db.models import get_db
from app.db.crud import get_index_stats

router = APIRouter()


class IndexPathRequest(BaseModel):
    path: str


@router.get("/index/status")
async def index_status(db: Session = Depends(get_db)):
    stats = get_index_stats(db)
    return {
        "status": "ok",
        "stats": stats,
    }


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
