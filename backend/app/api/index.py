from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.tasks.celery_app import index_directory_task
from app.db.models import get_db
from app.db.crud import get_index_stats
from app.indexer.embedder import COLLECTION_NAME, _get_index_metadata, _get_current_embed_model, _get_vector_dimension, INDEX_VERSION

router = APIRouter()

try:
    from qdrant_client import QdrantClient
    from app.config import settings
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    QDRANT_AVAILABLE = True
except Exception:
    QDRANT_AVAILABLE = False


class IndexPathRequest(BaseModel):
    path: str


class IndexVersionResponse(BaseModel):
    status: str  # ok, reindex_required, warning
    index_version: str
    embed_model: str
    vector_dim: int
    current_model: str
    current_dim: int
    compatible: bool
    meenvssage: str


@router.get("/index/status")
async def index_status(db: Session = Depends(get_db)):
    stats = get_index_stats(db)
    return {
        "status": "ok",
        "stats": stats,
    }


@router.get("/index/version", response_model=IndexVersionResponse)
async def get_index_version(db: Session = Depends(get_db)):
    """
    Проверяет совместимость текущей модели эмбеддингов с проиндексированными данными.
    
    Возвращает:
    - status: "ok" | "reindex_required" | "warning"
    - compatible: True если можно искать, False если требуется переиндексация
    """
    if not QDRANT_AVAILABLE:
        return IndexVersionResponse(
            status="warning",
            index_version="unknown",
            embed_model="unknown",
            vector_dim=0,
            current_model="unknown",
            current_dim=0,
            compatible=True,
            message="Qdrant client not available"
        )
    
    try:
        metadata = _get_index_metadata()
        current_model = _get_current_embed_model()
        current_dim = _get_vector_dimension()
        
        if not metadata:
            # Индекс существует но metadata нет (старый индекс)
            if qdrant.collection_exists(COLLECTION_NAME):
                return IndexVersionResponse(
                    status="warning",
                    index_version="legacy",
                    embed_model="unknown",
                    vector_dim=0,
                    current_model=current_model,
                    current_dim=current_dim,
                    compatible=True,
                    message="Legacy index without metadata. Reindex recommended."
                )
            else:
                return IndexVersionResponse(
                    status="ok",
                    index_version=INDEX_VERSION,
                    embed_model="not_created",
                    vector_dim=0,
                    current_model=current_model,
                    current_dim=current_dim,
                    compatible=True,
                    message="Index not yet created"
                )
        
        indexed_version = metadata.get("index_version", "unknown")
        indexed_model = metadata.get("embed_model", "unknown")
        indexed_dim = metadata.get("vector_dim", 0)
        
        # Проверяем совместимость
        if indexed_dim and indexed_dim != current_dim:
            return IndexVersionResponse(
                status="reindex_required",
                index_version=indexed_version,
                embed_model=indexed_model,
                vector_dim=indexed_dim,
                current_model=current_model,
                current_dim=current_dim,
                compatible=False,
                message=f"Dimension mismatch: {indexed_dim}d vs {current_dim}d. Reindex required."
            )
        
        # Модель совпадает по размерности
        if indexed_model != current_model:
            return IndexVersionResponse(
                status="warning",
                index_version=indexed_version,
                embed_model=indexed_model,
                vector_dim=indexed_dim,
                current_model=current_model,
                current_dim=current_dim,
                compatible=True,
                message=f"Model changed but dimension matches. Reindex recommended."
            )
        
        # Полная совместимость
        return IndexVersionResponse(
            status="ok",
            index_version=indexed_version,
            embed_model=indexed_model,
            vector_dim=indexed_dim,
            current_model=current_model,
            current_dim=current_dim,
            compatible=True,
            message="Index compatible with current model"
        )
        
    except Exception as e:
        return IndexVersionResponse(
            status="error",
            index_version="error",
            embed_model="error",
            vector_dim=0,
            current_model="error",
            current_dim=0,
            compatible=False,
            message=str(e)
        )


@router.post("/index/trigger")
async def trigger_index(background_tasks: BackgroundTasks):
    from app.config import settings
    for path in settings.get_index_paths():
        index_directory_task.delay(path)
    return {"message": "Indexing triggered"}


@router.post("/index/add-path")
async def add_path(req: IndexPathRequest):
    index_directory_task.delay(req.path)
    return {"message": f"Indexing started for {req.path}"}
