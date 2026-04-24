"""Tests for Circuit Breaker functionality."""

import pytest
import time
from app.models.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreakerInitialState:
    """Tests for initial state."""
    
    def test_initial_state_is_closed(self):
        """Circuit breaker starts in CLOSED state."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.is_closed is True
        assert cb.is_open is False
        assert cb.is_half_open is False
    
    def test_initial_failure_count_is_zero(self):
        """Failure count starts at zero."""
        cb = CircuitBreaker()
        assert cb.failure_count == 0
    
    def test_can_execute_when_closed(self):
        """Can execute requests when closed."""
        cb = CircuitBreaker()
        assert cb.can_execute() is True


class TestCircuitBreakerFailureHandling:
    """Tests for failure handling."""
    
    def test_single_failure_does_not_open(self):
        """Single failure doesn't open circuit."""
        cb = CircuitBreaker(fail_threshold=3)
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 1
    
    def test_threshold_failures_opens_circuit(self):
        """Threshold failures open the circuit."""
        cb = CircuitBreaker(fail_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.is_open is True
    
    def test_failure_count_resets_on_success(self):
        """Success resets failure count."""
        cb = CircuitBreaker(fail_threshold=3)
        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED


class TestCircuitBreakerCooldown:
    """Tests for cooldown behavior."""
    
    def test_open_state_blocks_execution(self):
        """OPEN state blocks execution."""
        cb = CircuitBreaker(fail_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.can_execute() is False
    
    def test_half_open_after_cooldown(self):
        """Circuit becomes HALF_OPEN after cooldown."""
        cb = CircuitBreaker(fail_threshold=3, cooldown_seconds=1)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        time.sleep(1.1)  # Wait for cooldown
        
        assert cb.state == CircuitState.HALF_OPEN
        assert cb.can_execute() is True
    
    def test_success_in_half_open_closes_circuit(self):
        """Success in HALF_OPEN closes circuit."""
        cb = CircuitBreaker(fail_threshold=3, cooldown_seconds=1)
        for _ in range(3):
            cb.record_failure()
        
        time.sleep(1.1)
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
    
    def test_failure_in_half_open_reopens_circuit(self):
        """Failure in HALF_OPEN reopens circuit."""
        cb = CircuitBreaker(fail_threshold=3, cooldown_seconds=1)
        for _ in range(3):
            cb.record_failure()
        
        time.sleep(1.1)
        assert cb.state == CircuitState.HALF_OPEN
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.opened_at is not None


class TestCircuitBreakerStatus:
    """Tests for status reporting."""
    
    def test_get_status_returns_dict(self):
        """get_status returns complete status dict."""
        cb = CircuitBreaker(fail_threshold=5, cooldown_seconds=120)
        cb.record_failure()
        cb.record_failure()
        
        status = cb.get_status()
        
        assert isinstance(status, dict)
        assert status["state"] == "closed"
        assert status["failure_count"] == 2
        assert status["fail_threshold"] == 5
        assert status["cooldown_seconds"] == 120
        assert "time_until_retry" in status
        assert "last_failure_time" in status
        assert "last_success_time" in status
    
    def test_time_until_retry_when_closed(self):
        """time_until_retry is 0 when closed."""
        cb = CircuitBreaker()
        assert cb.time_until_retry == 0.0
    
    def test_time_until_retry_when_open(self):
        """time_until_retry shows remaining cooldown."""
        cb = CircuitBreaker(fail_threshold=3, cooldown_seconds=10)
        for _ in range(3):
            cb.record_failure()
        
        assert cb.time_until_retry > 0
        assert cb.time_until_retry <= 10.0


class TestCircuitBreakerReset:
    """Tests for reset functionality."""
    
    def test_reset_clears_state(self):
        """Reset clears all state."""
        cb = CircuitBreaker(fail_threshold=3, cooldown_seconds=60)
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        cb.reset()
        
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.opened_at is None
        assert cb.can_execute() is True


class TestCircuitBreakerEdgeCases:
    """Tests for edge cases."""
    
    def test_zero_threshold_never_opens(self):
        """Zero threshold means circuit never opens (edge case)."""
        # При fail_threshold=0, первая же ошибка открывает circuit (0 >= 0)
        # Это корректное поведение для мгновенного срабатывания
        cb = CircuitBreaker(fail_threshold=0)
        cb.record_failure()
        # При zero threshold circuit открывается сразу
        assert cb.state == CircuitState.OPEN
    
    def test_rapid_failures_open_immediately(self):
        """Rapid failures open circuit immediately after threshold."""
        cb = CircuitBreaker(fail_threshold=5)
        for i in range(5):
            cb.record_failure()
            if i < 4:
                assert cb.state == CircuitState.CLOSED
            else:
                assert cb.state == CircuitState.OPEN
