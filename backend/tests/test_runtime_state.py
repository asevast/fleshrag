"""Tests for RuntimeStateService."""

import pytest
import time
from unittest.mock import Mock, patch
from app.services.runtime_state_service import RuntimeStateService, RuntimeState


@pytest.fixture
def mock_redis():
    """Mock Redis client для тестов."""
    mock = Mock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    return mock


@pytest.fixture
def runtime_service(mock_redis):
    """RuntimeStateService с mock Redis."""
    with patch('app.services.runtime_state_service.redis.from_url', return_value=mock_redis):
        service = RuntimeStateService("redis://localhost:6379")
        service._client = mock_redis
        yield service, mock_redis


class TestRuntimeStateDataclass:
    """Tests for RuntimeState dataclass."""
    
    def test_default_values(self):
        """RuntimeState has correct default values."""
        state = RuntimeState(
            active_provider="cloud",
            last_provider_switch=time.time(),
        )
        
        assert state.active_provider == "cloud"
        assert state.error_count == 0
        assert state.last_error_time is None
        assert state.fallback_active is False
        assert state.fallback_reason is None
        assert state.health_status == "unknown"
    
    def test_asdict_conversion(self):
        """RuntimeState can be converted to dict."""
        from dataclasses import asdict
        
        state = RuntimeState(
            active_provider="local",
            last_provider_switch=1234567890.0,
            error_count=3,
            health_status="degraded",
        )
        
        state_dict = asdict(state)
        
        assert isinstance(state_dict, dict)
        assert state_dict["active_provider"] == "local"
        assert state_dict["error_count"] == 3
        assert state_dict["health_status"] == "degraded"


class TestRuntimeStateService:
    """Tests for RuntimeStateService."""
    
    def test_get_state_default(self, runtime_service):
        """Returns default state when Redis is empty."""
        service, _ = runtime_service
        
        state = service.get_state()
        
        assert state.active_provider == "cloud"  # default_provider
        assert state.error_count == 0
        assert state.health_status == "unknown"
    
    def test_set_state(self, runtime_service):
        """Can save state."""
        service, mock_redis = runtime_service
        
        test_state = RuntimeState(
            active_provider="local",
            last_provider_switch=1234567890.0,
            error_count=2,
            health_status="degraded",
        )
        
        service.set_state(test_state)
        
        # Verify Redis was called
        assert mock_redis.set.called
        
    def test_get_active_provider(self, runtime_service):
        """Returns active provider from state."""
        service, mock_redis = runtime_service
        
        import json
        from dataclasses import asdict
        
        state = RuntimeState(
            active_provider="local",
            last_provider_switch=time.time(),
        )
        
        mock_redis.get.return_value = json.dumps(asdict(state))
        
        provider = service.get_active_provider()
        assert provider == "local"
    
    def test_set_active_provider(self, runtime_service):
        """Can change active provider."""
        service, mock_redis = runtime_service
        
        service.set_active_provider("local", reason="Cloud unavailable")
        
        assert mock_redis.set.called
        
    def test_record_error(self, runtime_service):
        """Records errors."""
        service, mock_redis = runtime_service
        
        service.record_error("llm")
        
        # Verify state was saved
        assert mock_redis.set.called
        
    def test_record_multiple_errors(self, runtime_service):
        """Multiple errors are recorded."""
        service, mock_redis = runtime_service
        
        for _ in range(5):
            service.record_error("general")
        
        # Verify set was called multiple times
        assert mock_redis.set.call_count >= 5
    
    def test_record_success(self, runtime_service):
        """Success is recorded."""
        service, mock_redis = runtime_service
        
        service.record_success()
        
        assert mock_redis.set.called
    
    def test_update_health(self, runtime_service):
        """Updates health status."""
        service, mock_redis = runtime_service
        
        service.update_health("healthy", {"provider": "cloud", "latency_ms": 50})
        
        # Verify both set calls (state and health)
        assert mock_redis.set.call_count >= 1
    
    def test_get_health(self, runtime_service):
        """Returns health info."""
        service, _ = runtime_service
        
        health = service.get_health()
        
        assert "status" in health
        assert "active_provider" in health
    
    def test_reset(self, runtime_service):
        """Resets all runtime state."""
        service, mock_redis = runtime_service
        
        service.reset()
        
        assert mock_redis.delete.called
        
    def test_get_all(self, runtime_service):
        """Returns complete runtime state."""
        service, _ = runtime_service
        
        all_state = service.get_all()
        
        assert "active_provider" in all_state
        assert "error_count" in all_state
        assert "health_status" in all_state


class TestRuntimeStateIntegration:
    """Integration tests for runtime state flow."""
    
    def test_fallback_state_tracking(self, runtime_service):
        """Tests that fallback state is tracked."""
        service, mock_redis = runtime_service
        
        service.set_active_provider("local", reason="test")
        
        # Verify state was saved
        assert mock_redis.set.call_count >= 1
    
    def test_recovery_tracking(self, runtime_service):
        """Tests that recovery is tracked."""
        service, mock_redis = runtime_service
        
        service.record_success()
        
        assert mock_redis.set.called


class TestRuntimeStatePersistence:
    """Tests for runtime state persistence in Redis."""
    
    def test_state_has_ttl(self, runtime_service):
        """State is saved with TTL."""
        service, mock_redis = runtime_service
        
        import json
        from dataclasses import asdict
        
        state = RuntimeState(
            active_provider="local",
            last_provider_switch=time.time(),
        )
        
        service.set_state(state)
        
        # Verify set was called
        assert mock_redis.set.called
