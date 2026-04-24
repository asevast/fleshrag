"""
Runtime State Service для хранения runtime-состояния в Redis.

Разделяет persistent settings (SQLite) и runtime state (Redis):
- Persistent: конфигурация, настройки пользователя
- Runtime: active provider с fallback, circuit breaker state, error streaks
"""

from __future__ import annotations

import json
import time
from typing import Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

import redis

from app.config import settings


@dataclass
class RuntimeState:
    """Runtime state для активного провайдера."""
    active_provider: str
    last_provider_switch: float
    error_count: int = 0
    last_error_time: Optional[float] = None
    fallback_active: bool = False
    fallback_reason: Optional[str] = None
    last_health_check: Optional[float] = None
    health_status: str = "unknown"  # healthy, degraded, unhealthy


class RuntimeStateService:
    """
    Сервис для управления runtime state в Redis.
    
    Runtime state включает:
    - active_provider (с учётом fallback)
    - error streaks
    - transient health status
    - circuit breaker state
    
    Не включает:
    - permanent settings (LLM model, embed model, etc.)
    - user preferences
    - index configuration
    """
    
    PREFIX = "runtime:"
    KEYS = {
        "state": "runtime:state",
        "error_streak": "runtime:error_streak",
        "health": "runtime:health",
        "provider_switch": "runtime:provider_switch",
    }
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.redis_url
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """Ленивая инициализация Redis клиента."""
        if self._client is None:
            self._client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=5.0,
                socket_connect_timeout=5.0,
            )
        return self._client
    
    def get_state(self) -> RuntimeState:
        """Получает текущее runtime state."""
        try:
            data = self.client.get(self.KEYS["state"])
            if data:
                state_dict = json.loads(data)
                return RuntimeState(**state_dict)
        except Exception:
            pass
        
        # Default state
        return RuntimeState(
            active_provider=settings.default_provider,
            last_provider_switch=time.time(),
            error_count=0,
            health_status="unknown",
        )
    
    def set_state(self, state: RuntimeState):
        """Сохраняет runtime state."""
        try:
            self.client.set(
                self.KEYS["state"],
                json.dumps(asdict(state)),
                ex=3600,  # TTL 1 час
            )
        except Exception as e:
            print(f"Error saving runtime state: {e}")
    
    def get_active_provider(self) -> str:
        """Получает активного провайдера (с учётом fallback)."""
        state = self.get_state()
        return state.active_provider
    
    def set_active_provider(self, provider: str, reason: str = None):
        """Устанавливает активного провайдера."""
        state = self.get_state()
        state.active_provider = provider
        state.last_provider_switch = time.time()
        
        if reason:
            state.fallback_active = (provider != settings.default_provider)
            state.fallback_reason = reason
        
        self.set_state(state)
    
    def record_error(self, error_type: str = "general"):
        """Записывает ошибку для tracking error streaks."""
        state = self.get_state()
        state.error_count += 1
        state.last_error_time = time.time()
        
        # Если ошибок > 5 за последний час — помечаем как degraded
        if state.error_count >= 5:
            state.health_status = "degraded"
            state.fallback_active = True
            state.fallback_reason = f"High error rate: {state.error_count} errors"
        
        self.set_state(state)
        
        # Также записываем в error streak для детального tracking
        self._increment_error_streak(error_type)
    
    def record_success(self):
        """Записывает успех для сброса error streaks."""
        state = self.get_state()
        state.error_count = max(0, state.error_count - 1)
        state.health_status = "healthy" if state.error_count < 3 else "degraded"
        state.fallback_active = False
        state.fallback_reason = None
        
        self.set_state(state)
        self._reset_error_streak()
    
    def _increment_error_streak(self, error_type: str):
        """Увеличивает счетчик ошибок для конкретного типа."""
        key = f"{self.KEYS['error_streak']}:{error_type}"
        try:
            count = int(self.client.get(key) or 0)
            self.client.set(key, count + 1, ex=3600)  # TTL 1 час
        except Exception:
            pass
    
    def _reset_error_streak(self):
        """Сбрасывает все error streaks."""
        try:
            for error_type in ["general", "llm", "embed", "rerank"]:
                key = f"{self.KEYS['error_streak']}:{error_type}"
                self.client.delete(key)
        except Exception:
            pass
    
    def update_health(self, status: str, details: dict = None):
        """Обновляет health status."""
        state = self.get_state()
        state.health_status = status
        state.last_health_check = time.time()
        
        if details:
            # Сохраняем детали отдельно
            self.client.set(
                self.KEYS["health"],
                json.dumps(details),
                ex=300,  # TTL 5 минут
            )
        
        self.set_state(state)
    
    def get_health(self) -> dict:
        """Получает health status."""
        try:
            data = self.client.get(self.KEYS["health"])
            if data:
                return json.loads(data)
        except Exception:
            pass
        
        state = self.get_state()
        return {
            "status": state.health_status,
            "last_check": state.last_health_check,
            "active_provider": state.active_provider,
            "error_count": state.error_count,
        }
    
    def reset(self):
        """Сбрасывает runtime state к дефолтным значениям."""
        try:
            for key in self.KEYS.values():
                self.client.delete(key)
        except Exception:
            pass
    
    def get_all(self) -> dict:
        """Получает полное runtime state для API."""
        state = self.get_state()
        health = self.get_health()
        
        return {
            "active_provider": state.active_provider,
            "last_provider_switch": datetime.fromtimestamp(state.last_provider_switch).isoformat(),
            "error_count": state.error_count,
            "last_error_time": datetime.fromtimestamp(state.last_error_time).isoformat() if state.last_error_time else None,
            "fallback_active": state.fallback_active,
            "fallback_reason": state.fallback_reason,
            "health_status": state.health_status,
            "last_health_check": datetime.fromtimestamp(state.last_health_check).isoformat() if state.last_health_check else None,
            "health_details": health,
        }
