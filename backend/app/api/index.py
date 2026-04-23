import os
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import List, Optional

from app.tasks.celery_app import index_directory_task, index_file_task
from app.db.models import get_db, IndexedFile
from app.db.crud import get_index_stats, get_index_paths, add_index_path, remove_index_path
from app.config import settings

router = APIRouter()


class IndexPathRequest(BaseModel):
    path: str


class PathsRequest(BaseModel):
    paths: Optional[List[str]] = None


@router.get("/index/status")
async def index_status(db: Session = Depends(get_db)):
    stats = get_index_stats(db)
    recent_errors = (
        db.query(IndexedFile)
        .filter(IndexedFile.status == "error")
        .order_by(IndexedFile.indexed_at.desc())
        .limit(10)
        .all()
    )
    return {
        "status": "ok",
        "stats": stats,
        "recent_errors": [
            {
                "path": f.path,
                "filename": f.filename,
                "error_message": f.error_message,
                "indexed_at": f.indexed_at,
            }
            for f in recent_errors
        ],
    }


@router.post("/index/trigger")
async def trigger_index(req: Optional[PathsRequest] = None, background_tasks: BackgroundTasks = None):
    """
    Запуск индексации.
    Если переданы paths - индексирует указанные пути, иначе - все пути из конфига.
    """
    if req and req.paths:
        for path in req.paths:
            if not os.path.exists(path):
                raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")
            index_directory_task.delay(path)
    else:
        for path in settings.index_paths.split(":"):
            if path and os.path.exists(path):
                index_directory_task.delay(path)
    return {"message": "Indexing triggered"}


@router.get("/index/paths")
async def list_paths(db: Session = Depends(get_db)):
    """
    Получить список текущих путей для индексации из БД.
    """
    paths = get_index_paths(db, active_only=True)
    return {
        "paths": [p.path for p in paths]
    }


@router.post("/index/paths")
async def add_path(req: IndexPathRequest, db: Session = Depends(get_db)):
    """
    Добавить путь для индексации в БД и запустить индексацию.
    """
    if not os.path.exists(req.path):
        raise HTTPException(status_code=400, detail=f"Path does not exist: {req.path}")
    
    # Добавляем путь в БД
    existing = add_index_path(db, req.path)
    
    # Запускаем индексацию нового пути
    index_directory_task.delay(req.path)
    
    return {
        "message": f"Path {req.path} added to indexing",
        "path": req.path,
        "added": existing is None  # True если путь новый
    }


@router.delete("/index/paths/{path:path}")
async def remove_path(path: str, db: Session = Depends(get_db)):
    """
    Удалить путь из индексируемых.
    """
    # Удаляем файлы этого пути из БД indexed_files
    db.query(IndexedFile).filter(IndexedFile.path.like(f"{path}%")).delete()
    db.commit()
    
    # Удаляем путь из списка индексации
    removed = remove_index_path(db, path)
    
    if not removed:
        raise HTTPException(status_code=404, detail=f"Path {path} not found")
    
    return {
        "message": f"Path {path} removed from indexing",
        "path": path
    }
