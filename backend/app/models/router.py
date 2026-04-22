from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.providers import CloudProvider, LocalProvider
from app.services.settings_service import SettingsService


class ModelRouter:
    def __init__(self, db: Session | None = None):
        self.settings = SettingsService(db)

    def get_provider(self, provider: str | None = None):
        resolved_provider = provider or self.settings.get_active_provider()
        llm_model = self.settings.get_llm_model(resolved_provider)
        embed_model = self.settings.get_embed_model(resolved_provider)
        rerank_model = self.settings.get_rerank_model(resolved_provider)
        temperature = self.settings.get_temperature()
        max_tokens = self.settings.get_max_tokens()

        if resolved_provider == "cloud" and settings.neuraldeep_api_key:
            return CloudProvider(
                llm_model=llm_model,
                embed_model=embed_model,
                rerank_model=rerank_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        return LocalProvider(
            llm_model=llm_model,
            embed_model=embed_model,
            rerank_model=rerank_model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

