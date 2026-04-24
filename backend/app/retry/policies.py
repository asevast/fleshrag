"""
Retry и Timeout политики для различных операций.

Определяет стратегии повторных попыток и таймауты для:
- embeddings
- chat/completion
- rerank
- transcription
- OCR
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Callable, TypeVar, Any
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class RetryPolicy:
    """Конфигурация политики повторных попыток."""
    max_retries: int = 3
    base_delay: float = 1.0  # секунды
    max_delay: float = 30.0  # секунды
    exponential_backoff: bool = True
    retryable_exceptions: tuple | None = None
    
    def get_delay(self, attempt: int) -> float:
        """Вычисляет задержку перед повторной попыткой."""
        if self.exponential_backoff:
            delay = self.base_delay * (2 ** attempt)
        else:
            delay = self.base_delay
        
        return min(delay, self.max_delay)


@dataclass
class TimeoutConfig:
    """Конфигурация таймаутов."""
    connect_timeout: float = 10.0
    read_timeout: float = 60.0
    total_timeout: float = 120.0


# Предопределённые политики для разных операций
POLICIES = {
    "embeddings": RetryPolicy(
        max_retries=3,
        base_delay=1.0,
        max_delay=10.0,
        exponential_backoff=True,
    ),
    "chat": RetryPolicy(
        max_retries=2,
        base_delay=2.0,
        max_delay=30.0,
        exponential_backoff=True,
    ),
    "rerank": RetryPolicy(
        max_retries=2,
        base_delay=0.5,
        max_delay=5.0,
        exponential_backoff=False,
    ),
    "transcription": RetryPolicy(
        max_retries=1,  # Дорогая операция, минимум повторов
        base_delay=5.0,
        max_delay=10.0,
        exponential_backoff=False,
    ),
    "ocr": RetryPolicy(
        max_retries=2,
        base_delay=1.0,
        max_delay=5.0,
        exponential_backoff=False,
    ),
    "search": RetryPolicy(
        max_retries=2,
        base_delay=0.5,
        max_delay=5.0,
        exponential_backoff=False,
    ),
}

TIMEOUT_CONFIGS = {
    "embeddings": TimeoutConfig(connect_timeout=5.0, read_timeout=30.0, total_timeout=60.0),
    "chat": TimeoutConfig(connect_timeout=10.0, read_timeout=120.0, total_timeout=180.0),
    "rerank": TimeoutConfig(connect_timeout=5.0, read_timeout=15.0, total_timeout=30.0),
    "transcription": TimeoutConfig(connect_timeout=10.0, read_timeout=300.0, total_timeout=600.0),
    "ocr": TimeoutConfig(connect_timeout=5.0, read_timeout=30.0, total_timeout=60.0),
    "search": TimeoutConfig(connect_timeout=5.0, read_timeout=30.0, total_timeout=60.0),
}

T = TypeVar('T')


async def retry_with_backoff(
    func: Callable[..., T],
    policy: RetryPolicy | None = None,
    *args,
    **kwargs,
) -> T:
    """
    Выполняет функцию с экспоненциальным backoff при ошибках.
    
    Args:
        func: Асинхронная функция для выполнения
        policy: Политика повторных попыток (использует default если None)
        *args: Аргументы функции
        **kwargs: Именованные аргументы функции
    
    Returns:
        Результат выполнения функции
    
    Raises:
        Последняя ошибка если все попытки исчерпаны
    """
    if policy is None:
        policy = POLICIES["chat"]  # default policy
    
    last_exception = None
    
    for attempt in range(policy.max_retries):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        
        except Exception as e:
            last_exception = e
            
            # Проверяем можно ли повторить
            if policy.retryable_exceptions and not isinstance(e, policy.retryable_exceptions):
                raise
            
            if attempt < policy.max_retries - 1:
                delay = policy.get_delay(attempt)
                logger.warning(
                    f"Ошибка при выполнении {func.__name__}: {e}. "
                    f"Повтор через {delay:.1f}с (попытка {attempt + 1}/{policy.max_retries})"
                )
                await asyncio.sleep(delay)
            else:
                logger.error(
                    f"Исчерпаны все попытки для {func.__name__} после {policy.max_retries} повторов"
                )
    
    raise last_exception


def retry_async(policy_name: str = "chat"):
    """
    Декоратор для автоматического повторения асинхронных функций.
    
    Args:
        policy_name: Имя предопределённой политики из POLICIES
    
    Example:
        @retry_async("embeddings")
        async def fetch_embeddings(texts):
            ...
    """
    policy = POLICIES.get(policy_name, POLICIES["chat"])
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_with_backoff(func, policy, *args, **kwargs)
        return wrapper
    return decorator


def get_policy(operation_type: str) -> RetryPolicy:
    """
    Получает политику для типа операции.
    
    Args:
        operation_type: Тип операции (embeddings, chat, rerank, transcription, ocr, search)
    
    Returns:
        RetryPolicy для операции
    """
    return POLICIES.get(operation_type, POLICIES["chat"])


def get_timeout_config(operation_type: str) -> TimeoutConfig:
    """
    Получает конфигурацию таймаутов для типа операции.
    
    Args:
        operation_type: Тип операции
    
    Returns:
        TimeoutConfig для операции
    """
    return TIMEOUT_CONFIGS.get(operation_type, TIMEOUT_CONFIGS["chat"])


# Примеры использования в коде

async def example_embeddings_call(texts: list[str]):
    """Пример использования retry для embeddings."""
    from app.config import settings
    import httpx
    
    policy = get_policy("embeddings")
    timeout = get_timeout_config("embeddings")
    
    async def _do_embeddings():
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=timeout.connect_timeout,
                read=timeout.read_timeout,
                total=timeout.total_timeout,
            )
        ) as client:
            response = await client.post(
                f"{settings.embed_service_url}/embed",
                json={"texts": texts},
            )
            response.raise_for_status()
            return response.json()["embeddings"]
    
    return await retry_with_backoff(_do_embeddings, policy)


async def example_chat_call(prompt: str):
    """Пример использования retry для chat."""
    from app.config import settings
    import httpx
    
    policy = get_policy("chat")
    timeout = get_timeout_config("chat")
    
    async def _do_chat():
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=timeout.connect_timeout,
                read=timeout.read_timeout,
                total=timeout.total_timeout,
            )
        ) as client:
            response = await client.post(
                f"{settings.neuraldeep_base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.neuraldeep_api_key}"},
                json={"model": settings.cloud_llm_model, "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
    
    return await retry_with_backoff(_do_chat, policy)


async def example_transcription_call(audio_path: str):
    """Пример использования retry для транскрибации."""
    from app.indexer.parsers.audio import transcribe_audio
    
    policy = get_policy("transcription")
    
    # Для синхронной функции
    return await retry_with_backoff(transcribe_audio, policy, audio_path)
