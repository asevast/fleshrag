from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.db import crud


class SettingsService:
    def __init__(self, db: Session | None = None):
        self.db = db

    def _get(self, key: str, default: Any) -> Any:
        if self.db is None:
            return default
        value = crud.get_setting(self.db, key, None)
        return default if value is None else value

    def get_active_provider(self) -> str:
        provider = str(self._get("active_provider", settings.default_provider)).lower()
        valid_providers = {"cloud", "local", "local_embed"}
        return provider if provider in valid_providers else settings.default_provider

    def get_llm_model(self, provider: str | None = None) -> str:
        resolved_provider = provider or self.get_active_provider()
        default_model = (
            settings.cloud_llm_model if resolved_provider == "cloud" else settings.local_llm_model
        )
        return str(self._get("llm_model", default_model))

    def get_embed_model(self, provider: str | None = None) -> str:
        resolved_provider = provider or self.get_active_provider()
        default_model = (
            settings.cloud_embed_model if resolved_provider == "cloud" else settings.local_embed_model
        )
        return str(self._get("embed_model", default_model))

    def get_rerank_model(self, provider: str | None = None) -> str | None:
        resolved_provider = provider or self.get_active_provider()
        default_model = (
            settings.cloud_rerank_model if resolved_provider == "cloud" else settings.local_rerank_model
        )
        value = self._get("rerank_model", default_model)
        return None if value in {None, "", "none"} else str(value)

    def get_temperature(self) -> float:
        return float(self._get("llm_temperature", settings.llm_temperature))

    def get_max_tokens(self) -> int:
        return int(self._get("llm_max_tokens", settings.llm_max_tokens))

    def get_top_k_search(self) -> int:
        return int(self._get("top_k_search", settings.top_k_search))

    def get_top_k_rerank(self) -> int:
        return int(self._get("top_k_rerank", settings.top_k_rerank))

    def get_chunk_size(self) -> int:
        return int(self._get("chunk_size", settings.chunk_size))

    def get_chunk_overlap(self) -> int:
        return int(self._get("chunk_overlap", settings.chunk_overlap))

