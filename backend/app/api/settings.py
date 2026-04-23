from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.models import get_db
from app.db import crud
from app.config import settings as app_settings

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
    chunk_size: Optional[int] = Field(None, ge=64, le=2048)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=512)
    top_k_search: Optional[int] = Field(None, ge=1, le=100)
    top_k_rerank: Optional[int] = Field(None, ge=1, le=50)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """Получить текущие настройки."""
    return SettingsResponse(
        llm_model=app_settings.llm_model,
        embed_model=app_settings.embed_model,
        chunk_size=app_settings.chunk_size,
        chunk_overlap=app_settings.chunk_overlap,
        top_k_search=app_settings.top_k_search,
        top_k_rerank=app_settings.top_k_rerank,
        index_paths=app_settings.index_paths.split(":"),
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdate, db: Session = Depends(get_db)):
    """
    Обновить настройки (сохраняет в БД).
    
    Примечание: некоторые настройки (LLM_MODEL, EMBED_MODEL) требуют перезапуска сервисов.
    Настройки чанкинга применяются к новым файлам при индексации.
    """
    if req.llm_model:
        crud.set_setting(db, "llm_model", req.llm_model)
    if req.embed_model:
        crud.set_setting(db, "embed_model", req.embed_model)
    if req.chunk_size is not None:
        crud.set_setting(db, "chunk_size", str(req.chunk_size))
    if req.chunk_overlap is not None:
        crud.set_setting(db, "chunk_overlap", str(req.chunk_overlap))
    if req.top_k_search is not None:
        crud.set_setting(db, "top_k_search", str(req.top_k_search))
    if req.top_k_rerank is not None:
        crud.set_setting(db, "top_k_rerank", str(req.top_k_rerank))
    
    return SettingsResponse(
        llm_model=crud.get_setting(db, "llm_model", app_settings.llm_model),
        embed_model=crud.get_setting(db, "embed_model", app_settings.embed_model),
        chunk_size=int(crud.get_setting(db, "chunk_size", str(app_settings.chunk_size))),
        chunk_overlap=int(crud.get_setting(db, "chunk_overlap", str(app_settings.chunk_overlap))),
        top_k_search=int(crud.get_setting(db, "top_k_search", str(app_settings.top_k_search))),
        top_k_rerank=int(crud.get_setting(db, "top_k_rerank", str(app_settings.top_k_rerank))),
        index_paths=app_settings.index_paths.split(":"),
    )
