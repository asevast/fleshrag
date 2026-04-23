from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.providers import CloudProvider, LocalProvider
from app.services.settings_service import SettingsService


class ModelRouter:
    def __init__(self, db: Session | None = None):
        self.settings = SettingsService(db)
        self._provider = None

    @property
    def active_provider(self) -> str:
        """Возвращает имя активного провайдера (cloud/local)."""
        return self.settings.get_active_provider()

    def get_provider(self, provider: str | None = None):
        if provider:
            # Если указан явно — создаём новый экземпляр
            resolved_provider = provider
        elif self._provider is None:
            resolved_provider = self.settings.get_active_provider()
            self._provider = self._create_provider(resolved_provider)
        else:
            # Проверяем, не изменился ли провайдер в настройках
            current = self.settings.get_active_provider()
            if current != self._provider.capabilities.provider:
                self._provider = self._create_provider(current)
            return self._provider
        return self._create_provider(resolved_provider)

    def _create_provider(self, provider_name: str):
        llm_model = self.settings.get_llm_model(provider_name)
        embed_model = self.settings.get_embed_model(provider_name)
        rerank_model = self.settings.get_rerank_model(provider_name)
        temperature = self.settings.get_temperature()
        max_tokens = self.settings.get_max_tokens()

        if provider_name == "cloud" and settings.neuraldeep_api_key:
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

    def transcribe_audio(self, audio_path: str) -> str:
        """Транскрибирует аудио файл через текущий провайдер."""
        provider = self.get_provider()
        return provider.transcribe_audio(audio_path)

