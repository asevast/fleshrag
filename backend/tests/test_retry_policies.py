"""Tests for Retry/Timeout policies."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.retry.policies import (
    RetryPolicy,
    TimeoutConfig,
    retry_with_backoff,
    retry_async,
    get_policy,
    get_timeout_config,
    POLICIES,
    TIMEOUT_CONFIGS,
)


class TestRetryPolicy:
    """Tests for RetryPolicy."""
    
    def test_get_delay_exponential(self):
        """Экспоненциальный backoff."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=30.0,
            exponential_backoff=True,
        )
        
        assert policy.get_delay(0) == 1.0    # 1 * 2^0 = 1
        assert policy.get_delay(1) == 2.0    # 1 * 2^1 = 2
        assert policy.get_delay(2) == 4.0    # 1 * 2^2 = 4
        assert policy.get_delay(3) == 8.0    # 1 * 2^3 = 8
        assert policy.get_delay(10) == 30.0  # capped at max_delay
    
    def test_get_delay_linear(self):
        """Линейная задержка."""
        policy = RetryPolicy(
            base_delay=2.0,
            max_delay=10.0,
            exponential_backoff=False,
        )
        
        assert policy.get_delay(0) == 2.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 2.0
    
    def test_max_delay_cap(self):
        """Ограничение максимальной задержки."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=5.0,
            exponential_backoff=True,
        )
        
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0
        assert policy.get_delay(3) == 5.0  # capped
        assert policy.get_delay(10) == 5.0  # still capped


class TestTimeoutConfig:
    """Tests for TimeoutConfig."""
    
    def test_timeout_defaults(self):
        """Проверяет значения по умолчанию."""
        config = TimeoutConfig()
        assert config.connect_timeout == 10.0
        assert config.read_timeout == 60.0
        assert config.total_timeout == 120.0
    
    def test_timeout_custom(self):
        """Проверяет кастомные значения."""
        config = TimeoutConfig(
            connect_timeout=5.0,
            read_timeout=30.0,
            total_timeout=60.0,
        )
        assert config.connect_timeout == 5.0
        assert config.read_timeout == 30.0
        assert config.total_timeout == 60.0


class TestGetPolicy:
    """Tests for get_policy function."""
    
    def test_get_existing_policy(self):
        """Получает существующую политику."""
        policy = get_policy("embeddings")
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0
    
    def test_get_unknown_policy_returns_default(self):
        """Возвращает default policy для неизвестного типа."""
        policy = get_policy("unknown_operation")
        assert policy == POLICIES["chat"]


class TestGetTimeoutConfig:
    """Tests for get_timeout_config function."""
    
    def test_get_existing_timeout(self):
        """Получает существующую конфигурацию."""
        config = get_timeout_config("transcription")
        assert config.total_timeout == 600.0
    
    def test_get_unknown_timeout_returns_default(self):
        """Возвращает default config для неизвестного типа."""
        config = get_timeout_config("unknown")
        assert config == TIMEOUT_CONFIGS["chat"]


class TestRetryWithBackoff:
    """Tests for retry_with_backoff function."""
    
    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Успех с первой попытки."""
        async def success_func():
            return "success"
        
        result = await retry_with_backoff(success_func)
        assert result == "success"
    
    @pytest.mark.asyncio
    async def test_success_after_retry(self):
        """Успех после повтора."""
        call_count = 0
        
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Temporary error")
            return "success"
        
        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        result = await retry_with_backoff(flaky_func, policy)
        
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """Исчерпание всех повторов."""
        call_count = 0
        
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")
        
        policy = RetryPolicy(max_retries=3, base_delay=0.01)
        
        with pytest.raises(ValueError, match="Permanent error"):
            await retry_with_backoff(failing_func, policy)
        
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Неповторяемые исключения."""
        async def failing_func():
            raise TypeError("Not retryable")
        
        policy = RetryPolicy(
            max_retries=3,
            retryable_exceptions=(ValueError,),
        )
        
        # TypeError не в retryable_exceptions, сразу бросает
        with pytest.raises(TypeError, match="Not retryable"):
            await retry_with_backoff(failing_func, policy)
    
    @pytest.mark.asyncio
    async def test_sync_function(self):
        """Работает с синхронными функциями."""
        def sync_func():
            return "sync success"
        
        result = await retry_with_backoff(sync_func)
        assert result == "sync success"
    
    @pytest.mark.asyncio
    async def test_delay_between_retries(self):
        """Проверяет задержку между повторами."""
        call_times = []
        
        async def timing_func():
            call_times.append(asyncio.get_event_loop().time())
            if len(call_times) < 2:
                raise ValueError("Retry me")
            return "success"
        
        policy = RetryPolicy(max_retries=3, base_delay=0.1)
        await retry_with_backoff(timing_func, policy)
        
        # Проверяем что была задержка >= 0.08 (с допуском)
        delay = call_times[1] - call_times[0]
        assert delay >= 0.08


class TestRetryAsyncDecorator:
    """Tests for retry_async decorator."""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Успех с декоратором."""
        @retry_async("embeddings")
        async def decorated_func():
            return "decorated success"
        
        result = await decorated_func()
        assert result == "decorated success"
    
    @pytest.mark.asyncio
    async def test_decorator_retry(self):
        """Повтор с декоратором."""
        call_count = 0
        
        @retry_async("embeddings")
        async def flaky_decorated():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Retry")
            return "success"
        
        result = await flaky_decorated()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_decorator_preserves_metadata(self):
        """Сохраняет метаданные функции."""
        @retry_async("chat")
        async def my_custom_func(arg1, arg2):
            """Docstring."""
            pass
        
        assert my_custom_func.__name__ == "my_custom_func"
        assert my_custom_func.__doc__ == "Docstring."


class TestPoliciesConfiguration:
    """Tests for policy configurations."""
    
    def test_embeddings_policy(self):
        """Проверяет политику embeddings."""
        policy = POLICIES["embeddings"]
        assert policy.max_retries == 3
        assert policy.base_delay == 1.0
        assert policy.max_delay == 10.0
        assert policy.exponential_backoff is True
    
    def test_chat_policy(self):
        """Проверяет политику chat."""
        policy = POLICIES["chat"]
        assert policy.max_retries == 2
        assert policy.base_delay == 2.0
        assert policy.exponential_backoff is True
    
    def test_transcription_policy(self):
        """Проверяет политику transcription."""
        policy = POLICIES["transcription"]
        assert policy.max_retries == 1  # Минимум повторов для дорогих операций
        assert policy.base_delay == 5.0
    
    def test_embeddings_timeout(self):
        """Проверяет таймауты embeddings."""
        config = TIMEOUT_CONFIGS["embeddings"]
        assert config.total_timeout == 60.0
    
    def test_chat_timeout(self):
        """Проверяет таймауты chat."""
        config = TIMEOUT_CONFIGS["chat"]
        assert config.total_timeout == 180.0
        assert config.read_timeout == 120.0
    
    def test_transcription_timeout(self):
        """Проверяет таймауты transcription."""
        config = TIMEOUT_CONFIGS["transcription"]
        assert config.total_timeout == 600.0  # 10 минут для длинного аудио
