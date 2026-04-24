from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings as app_settings
from app.db import crud
from app.db.models import get_db
from app.services.settings_service import SettingsService

router = APIRouter()


class SettingsResponse(BaseModel):
    active_provider: str
    llm_model: str
    embed_model: str
    rerank_model: Optional[str] = None
    chunk_size: int
    chunk_overlap: int
    top_k_search: int
    top_k_rerank: int
    llm_temperature: float
    llm_max_tokens: int
    index_paths: List[str]


class SettingsUpdate(BaseModel):
    active_provider: Optional[str] = Field(None, pattern="^(cloud|local|local_embed)$")
    llm_model: Optional[str] = None
    embed_model: Optional[str] = None
    rerank_model: Optional[str] = None
    chunk_size: Optional[int] = Field(None, ge=64, le=2048)
    chunk_overlap: Optional[int] = Field(None, ge=0, le=512)
    top_k_search: Optional[int] = Field(None, ge=1, le=100)
    top_k_rerank: Optional[int] = Field(None, ge=1, le=50)
    llm_temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    llm_max_tokens: Optional[int] = Field(None, ge=1, le=32768)


def _serialize_settings(service: SettingsService) -> SettingsResponse:
    return SettingsResponse(
        active_provider=service.get_active_provider(),
        llm_model=service.get_llm_model(),
        embed_model=service.get_embed_model(),
        rerank_model=service.get_rerank_model(),
        chunk_size=service.get_chunk_size(),
        chunk_overlap=service.get_chunk_overlap(),
        top_k_search=service.get_top_k_search(),
        top_k_rerank=service.get_top_k_rerank(),
        llm_temperature=service.get_temperature(),
        llm_max_tokens=service.get_max_tokens(),
        index_paths=[path for path in app_settings.index_paths.split(":") if path],
    )


@router.get("/settings", response_model=SettingsResponse)
async def get_settings(db: Session = Depends(get_db)):
    """Получить текущие настройки runtime."""
    return _serialize_settings(SettingsService(db))


@router.put("/settings", response_model=SettingsResponse)
async def update_settings(req: SettingsUpdate, db: Session = Depends(get_db)):
    """Обновить runtime-настройки, сохраняемые в БД."""
    updates = req.model_dump(exclude_none=True)
    for key, value in updates.items():
        crud.set_setting(db, key, str(value))
    return _serialize_settings(SettingsService(db))
