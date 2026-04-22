from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.models import get_db
from app.db import crud
from app.config import settings as app_settings
from app.services.settings_service import SettingsService

router = APIRouter()


class SettingsResponse(BaseModel):
    active_provider: str
    llm_model: str
    embed_model: str
    rerank_model: Optional[str] = None
    llm_temperature: float
    llm_max_tokens: int
    chunk_size: int
    chunk_overlap: int
    top_k_search: int
    top_k_rerank: int
    index_paths: List[str]


class SettingsUpdate(BaseModel):
    active_provider: Optional[str] = Field(None, pattern="^(cloud|local)$")
    llm_model: Optional[str] = None
    embed_model: Optional[str] = None
    rerank_model: Optional[str] = None
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    llm_max_tokens: Optional[int] = Field(None, ge=64, le=8192)
    chunk_size: Optional[int] = Field(None, ge=64, le=2048)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=512)
    top_k_search: Optional[int] = Field(None, ge=1, le=100)
    top_k_rerank: Optional[int] = Field(None, ge=1, le=50)


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """Получить текущие настройки."""
    service = SettingsService(db)
    return SettingsResponse(
        active_provider=service.get_active_provider(),
        llm_model=service.get_llm_model(),
        embed_model=service.get_embed_model(),
        rerank_model=service.get_rerank_model(),
        llm_temperature=service.get_temperature(),
        llm_max_tokens=service.get_max_tokens(),
        chunk_size=service.get_chunk_size(),
        chunk_overlap=service.get_chunk_overlap(),
        top_k_search=service.get_top_k_search(),
        top_k_rerank=service.get_top_k_rerank(),
        index_paths=app_settings.index_paths.split(":"),
    )


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdate, db: Session = Depends(get_db)):
    """
    Обновить настройки (сохраняет в БД).
    
    Примечание: некоторые настройки (LLM_MODEL, EMBED_MODEL) требуют перезапуска сервисов.
    Настройки чанкинга применяются к новым файлам при индексации.
    """
    if req.active_provider:
        crud.set_setting(db, "active_provider", req.active_provider)
    if req.llm_model:
        crud.set_setting(db, "llm_model", req.llm_model)
    if req.embed_model:
        crud.set_setting(db, "embed_model", req.embed_model)
    if req.rerank_model is not None:
        crud.set_setting(db, "rerank_model", req.rerank_model)
    if req.llm_temperature is not None:
        crud.set_setting(db, "llm_temperature", str(req.llm_temperature))
    if req.llm_max_tokens is not None:
        crud.set_setting(db, "llm_max_tokens", str(req.llm_max_tokens))
    if req.chunk_size is not None:
        crud.set_setting(db, "chunk_size", str(req.chunk_size))
    if req.chunk_overlap is not None:
        crud.set_setting(db, "chunk_overlap", str(req.chunk_overlap))
    if req.top_k_search is not None:
        crud.set_setting(db, "top_k_search", str(req.top_k_search))
    if req.top_k_rerank is not None:
        crud.set_setting(db, "top_k_rerank", str(req.top_k_rerank))

    service = SettingsService(db)
    return SettingsResponse(
        active_provider=service.get_active_provider(),
        llm_model=service.get_llm_model(),
        embed_model=service.get_embed_model(),
        rerank_model=service.get_rerank_model(),
        llm_temperature=service.get_temperature(),
        llm_max_tokens=service.get_max_tokens(),
        chunk_size=service.get_chunk_size(),
        chunk_overlap=service.get_chunk_overlap(),
        top_k_search=service.get_top_k_search(),
        top_k_rerank=service.get_top_k_rerank(),
        index_paths=app_settings.index_paths.split(":"),
    )
