from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.models import get_db
from app.config import settings

router = APIRouter()


class SettingsResponse(BaseModel):
    llm_model: str
    embed_model: str
    chunk_size: int
    chunk_overlap: int
    top_k_search: int
    top_k_rerank: int
    index_paths: List[str]


class SettingsUpdate(BaseModel):
    llm_model: Optional[str] = None
    embed_model: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    top_k_search: Optional[int] = None
    top_k_rerank: Optional[int] = None
    index_paths: Optional[str] = None


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    return SettingsResponse(
        llm_model=settings.llm_model,
        embed_model=settings.embed_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        top_k_search=settings.top_k_search,
        top_k_rerank=settings.top_k_rerank,
        index_paths=settings.index_paths.split(":"),
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdate, db: Session = Depends(get_db)):
    # В текущей реализации настройки применяются только на уровне процесса
    # Для полноценного обновления требуется перезапуск сервисов
    # Здесь просто возвращаем текущие настройки с подтверждением запроса
    return SettingsResponse(
        llm_model=settings.llm_model,
        embed_model=settings.embed_model,
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        top_k_search=settings.top_k_search,
        top_k_rerank=settings.top_k_rerank,
        index_paths=settings.index_paths.split(":"),
    )
