"""
Circuit Breaker для защиты от временных ошибок cloud provider.

Состояния:
- CLOSED: нормальная работа, запросы проходят
- OPEN: провайдер недоступен, запросы блокируются
- HALF_OPEN: проверка восстановления после cooldown

Логика:
- После N последовательных ошибок → переход в OPEN
- Через T секунд → переход в HALF_OPEN
- Успешный запрос в HALF_OPEN → переход в CLOSED
- Ошибка в HALF_OPEN → возврат в OPEN
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Optional


class CircuitState(Enum):
    CLOSED = "closed"      # Нормальная работа
    OPEN = "open"          # Блокировка запросов
    HALF_OPEN = "half_open"  # Проверка восстановления


class CircuitBreaker:
    """
    Circuit Breaker для cloud provider.
    
    Атрибуты:
        fail_threshold: количество ошибок для перехода в OPEN
        cooldown_seconds: время ожидания перед попыткой восстановления
    """
    
    def __init__(
        self,
        fail_threshold: int = 3,
        cooldown_seconds: int = 60,
    ):
        self.fail_threshold = fail_threshold
        self.cooldown_seconds = cooldown_seconds
        
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._last_success_time: Optional[float] = None
        self._opened_at: Optional[float] = None
    
    @property
    def state(self) -> CircuitState:
        """Возвращает текущее состояние с учётом cooldown."""
        if self._state == CircuitState.OPEN:
            # Проверяем, истёк ли cooldown
            if self._opened_at is not None:
                elapsed = time.time() - self._opened_at
                if elapsed >= self.cooldown_seconds:
                    self._state = CircuitState.HALF_OPEN
        return self._state
    
    @property
    def is_closed(self) -> bool:
        return self.state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        return self.state == CircuitState.HALF_OPEN
    
    @property
    def failure_count(self) -> int:
        return self._failure_count
    
    @property
    def opened_at(self) -> Optional[float]:
        return self._opened_at
    
    @property
    def time_until_retry(self) -> float:
        """Время в секундах до следующей попытки (0 если не OPEN)."""
        if self._state != CircuitState.OPEN or self._opened_at is None:
            return 0.0
        elapsed = time.time() - self._opened_at
        return max(0.0, self.cooldown_seconds - elapsed)
    
    def can_execute(self) -> bool:
        """Проверяет, можно ли выполнить запрос."""
        state = self.state  # Автоматически обновляет состояние
        if state == CircuitState.CLOSED:
            return True
        if state == CircuitState.HALF_OPEN:
            return True
        return False
    
    def record_success(self):
        """Записывает успешный запрос."""
        self._failure_count = 0
        self._last_success_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            # Успех в HALF_OPEN → переход в CLOSED
            self._state = CircuitState.CLOSED
            self._opened_at = None
    
    def record_failure(self):
        """Записывает ошибку запроса."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            # Ошибка в HALF_OPEN → возврат в OPEN
            self._state = CircuitState.OPEN
            self._opened_at = time.time()
        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.fail_threshold:
                # Превышен порог ошибок → переход в OPEN
                self._state = CircuitState.OPEN
                self._opened_at = time.time()
    
    def reset(self):
        """Сбрасывает circuit breaker в начальное состояние."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = None
        self._last_success_time = None
        self._opened_at = None
    
    def get_status(self) -> dict:
        """Возвращает статус для monitoring."""
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "fail_threshold": self.fail_threshold,
            "cooldown_seconds": self.cooldown_seconds,
            "time_until_retry": round(self.time_until_retry, 1),
            "last_failure_time": self._last_failure_time,
            "last_success_time": self._last_success_time,
        }
