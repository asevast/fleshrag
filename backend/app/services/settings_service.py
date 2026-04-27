from __future__ import annotations

import re
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
        """
        Получает LLM модель для провайдера.
        
        Если provider='cloud' но в БД записана локальная модель — использует cloud модель по умолчанию.
        Если provider='local' но в БД записана cloud модель — использует local модель по умолчанию.
        
        Args:
            provider: Тип провайдера (cloud/local). Если None — использует active_provider.
        
        Returns:
            Название модели
        """
        resolved_provider = provider or self.get_active_provider()
        default_model = (
            settings.cloud_llm_model if resolved_provider == "cloud" else settings.local_llm_model
        )
        value = self._get("llm_model", default_model)
        
        # Если в БД записана модель но она не соответствует провайдеру — используем default
        if value != default_model:
            # Проверяем не交叉лась ли модель (cloud ↔ local)
            if resolved_provider == "cloud" and value == settings.local_llm_model:
                return default_model
            if resolved_provider == "local" and value == settings.cloud_llm_model:
                return default_model
        
        return str(value)

    def get_embed_model(self, provider: str | None = None) -> str:
        """
        Получает embedding модель для провайдера.
        
        Args:
            provider: Тип провайдера (cloud/local). Если None — использует active_provider.
        
        Returns:
            Название модели
        """
        resolved_provider = provider or self.get_active_provider()
        default_model = (
            settings.cloud_embed_model if resolved_provider == "cloud" else settings.local_embed_model
        )
        value = self._get("embed_model", default_model)
        
        # Если в БД записана модель но она не соответствует провайдеру — используем default
        if value != default_model:
            if resolved_provider == "cloud" and value == settings.local_embed_model:
                return default_model
            if resolved_provider == "local" and value == settings.cloud_embed_model:
                return default_model
        
        return str(value)

    def get_rerank_model(self, provider: str | None = None) -> str | None:
        """
        Получает rerank модель для провайдера.
        
        Args:
            provider: Тип провайдера (cloud/local). Если None — использует active_provider.
        
        Returns:
            Название модели или None
        """
        resolved_provider = provider or self.get_active_provider()
        default_model = (
            settings.cloud_rerank_model if resolved_provider == "cloud" else settings.local_rerank_model
        )
        value = self._get("rerank_model", default_model)
        
        # Если в БД записана модель но она не соответствует провайдеру — используем default
        if value and value != default_model:
            if resolved_provider == "cloud" and value == settings.local_rerank_model:
                value = default_model
            if resolved_provider == "local" and value == settings.cloud_rerank_model:
                value = default_model
        
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

    def get_index_paths(self) -> list[str]:
        """
        Получает пути индексации из БД.

        Если в БД не настроено — использует fallback из .env.
        
        Returns:
            Список путей для индексации
        """
        if self.db is None:
            return settings.get_index_paths()
        
        value = crud.get_setting(self.db, "index_paths", None)
        if value is None:
            # Fallback на .env
            return settings.get_index_paths()
        
        # Парсим строку из БД (разделитель ; для Windows, : для Linux)
        import re
        has_windows_paths = bool(re.search(r'[A-Za-z]:', value))
        if has_windows_paths:
            return [p.strip() for p in value.split(";") if p.strip()]
        else:
            return [p.strip() for p in value.split(":") if p.strip()]

    def set_index_paths(self, paths: list[str]):
        """
        Устанавливает пути индексации в БД.
        
        Args:
            paths: Список путей для индексации
        """
        if self.db is None:
            raise RuntimeError("Database session is required")
        
        # Сохраняем как строку с разделителем
        has_windows_paths = any(re.search(r'[A-Za-z]:', p) for p in paths)
        separator = ";" if has_windows_paths else ":"
        value = separator.join(paths)
        crud.set_setting(self.db, "index_paths", value)

