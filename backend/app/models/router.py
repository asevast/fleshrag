from __future__ import annotations

from sqlalchemy.orm import Session

from app.config import settings
from app.models.circuit_breaker import CircuitBreaker
from app.models.providers import CloudProvider, LocalProvider
from app.services.runtime_state_service import RuntimeStateService
from app.services.settings_service import SettingsService


class ModelRouter:
    """
    Router для переключения между cloud/local провайдерами.
    
    Атрибуты:
        circuit_breaker: CircuitBreaker для cloud provider
        runtime_state: RuntimeStateService для tracking состояния
        settings: SettingsService для persistent configuration
    """
    
    def __init__(self, db: Session | None = None):
        self.settings = SettingsService(db)
        self.runtime_state = RuntimeStateService()
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
        # Runtime state имеет приоритет над persistent settings
        return self.runtime_state.get_active_provider()
    
    @property
    def circuit_breaker_state(self) -> str:
        """Возвращает состояние circuit breaker."""
        return self.circuit_breaker.state.value

    @property
    def runtime_health(self) -> dict:
        """Возвращает runtime health status."""
        return self.runtime_state.get_health()

    def get_provider(self, provider: str | None = None):
        """
        Возвращает провайдера с учётом circuit breaker и runtime state.
        
        Если provider="cloud" но circuit breaker в состоянии OPEN,
        создаёт CloudProvider но circuit breaker предотвратит запрос.
        """
        if provider:
            # Если указан явно — создаём новый экземпляр
            resolved_provider = provider
        elif self._provider is None:
            resolved_provider = self.active_provider
            self._provider = self._create_provider(resolved_provider)
        else:
            # Проверяем, не изменился ли провайдер в runtime state
            current = self.active_provider
            if current != self._provider.capabilities.provider:
                self._provider = self._create_provider(current)
            return self._provider
        
        # Проверяем circuit breaker для cloud provider
        # Если OPEN — не блокируем, но записываем warning
        if resolved_provider == "cloud" and not self.circuit_breaker.can_execute():
            logger.warning(
                f"Circuit breaker open ({self.circuit_breaker.failure_count} failures), "
                f"but using cloud provider as requested"
            )
            # Не переключаем на local — пользователь явно выбрал cloud

        # Записываем успех если используем cloud
        if resolved_provider == "cloud":
            self.runtime_state.record_success()
        
        return self._create_provider(resolved_provider)
    
    def _get_local_provider(self):
        """Возвращает локальный провайдера (кэшируется)."""
        if self._local_provider is None:
            self._local_provider = self._create_provider("local")
        return self._local_provider

    def _create_provider(self, provider_name: str):
        """
        Создаёт провайдера для указанного типа.
        
        Если provider_name="cloud" — всегда создаёт CloudProvider,
        даже если API key не настроен (ошибка будет при runtime).
        """
        llm_model = self.settings.get_llm_model(provider_name)
        embed_model = self.settings.get_embed_model(provider_name)
        rerank_model = self.settings.get_rerank_model(provider_name)
        temperature = self.settings.get_temperature()
        max_tokens = self.settings.get_max_tokens()

        if provider_name == "cloud":
            # Всегда создаём CloudProvider если выбран cloud
            # Проверка API key будет при runtime запросе
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
        self.runtime_state.record_success()
    
    def record_cloud_failure(self):
        """Записывает ошибку запроса к cloud provider."""
        self.circuit_breaker.record_failure()
        self.runtime_state.record_error("llm")

        # Если circuit breaker открыт — переключаемся на local
        if self.circuit_breaker.is_open:
            self.runtime_state.set_active_provider(
                "local",
                reason=f"Circuit breaker opened after {self.circuit_breaker.failure_count} failures"
            )

    def transcribe_audio(self, audio_path: str) -> str:
        """Транскрибирует аудио файл через текущий провайдер."""
        provider = self.get_provider()
        return provider.transcribe_audio(audio_path)

    def get_runtime_status(self) -> dict:
        """Возвращает полное runtime состояние для API."""
        return {
            "active_provider": self.active_provider,
            "circuit_breaker": self.circuit_breaker.get_status(),
            "health": self.runtime_health,
            "runtime_details": self.runtime_state.get_all(),
        }

