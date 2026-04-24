from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.circuit_breaker import CircuitBreaker
from app.models.providers import CloudProvider, LocalProvider
from app.services.settings_service import SettingsService


class ModelRouter:
    """
    Router для переключения между cloud/local провайдерами.
    
    Атрибуты:
        circuit_breaker: CircuitBreaker для cloud provider
    """
    
    def __init__(self, db: Session | None = None):
        self.settings = SettingsService(db)
        self._provider = None
        self._local_provider = None
        # Circuit breaker только для cloud provider
        self.circuit_breaker = CircuitBreaker(
            fail_threshold=3,
            cooldown_seconds=60,
        )

    @property
    def active_provider(self) -> str:
        """Возвращает имя активного провайдера (cloud/local)."""
        return self.settings.get_active_provider()
    
    @property
    def circuit_breaker_state(self) -> str:
        """Возвращает состояние circuit breaker."""
        return self.circuit_breaker.state.value

    def get_provider(self, provider: str | None = None):
        """
        Возвращает провайдера с учётом circuit breaker.
        
        Если provider="cloud" но circuit breaker в состоянии OPEN,
        автоматически переключается на local.
        """
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
        
        # Проверяем circuit breaker для cloud provider
        if resolved_provider == "cloud" and not self.circuit_breaker.can_execute():
            # Cloud недоступен, используем local
            return self._get_local_provider()
        
        return self._create_provider(resolved_provider)
    
    def _get_local_provider(self):
        """Возвращает локальный провайдер (кэшируется)."""
        if self._local_provider is None:
            self._local_provider = self._create_provider("local")
        return self._local_provider

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
    
    def record_cloud_success(self):
        """Записывает успешный запрос к cloud provider."""
        self.circuit_breaker.record_success()
    
    def record_cloud_failure(self):
        """Записывает ошибку запроса к cloud provider."""
        self.circuit_breaker.record_failure()

    def transcribe_audio(self, audio_path: str) -> str:
        """Транскрибирует аудио файл через текущий провайдер."""
        provider = self.get_provider()
        return provider.transcribe_audio(audio_path)

