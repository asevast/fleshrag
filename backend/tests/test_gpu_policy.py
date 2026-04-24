"""Tests for GPU Policy Manager."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.gpu.policy import (
    GPUInfo,
    GPUPolicy,
    GPUDetector,
    GPUPolicyManager,
    get_device_for_task,
    can_use_gpu,
)


class TestGPUInfo:
    """Tests for GPUInfo dataclass."""
    
    def test_gpu_info_creation(self):
        """Создаёт GPUInfo."""
        gpu = GPUInfo(
            index=0,
            name="NVIDIA RTX 3080",
            total_memory_gb=10.0,
        )
        
        assert gpu.index == 0
        assert gpu.name == "NVIDIA RTX 3080"
        assert gpu.total_memory_gb == 10.0
        assert gpu.available is True


class TestGPUPolicy:
    """Tests for GPUPolicy dataclass."""
    
    def test_policy_defaults(self):
        """Проверяет значения по умолчанию."""
        policy = GPUPolicy()
        
        assert policy.enabled is True
        assert policy.reserved_memory_gb == 2.0
        assert policy.max_usage_percent == 0.8
        assert policy.allow_transcription is True
        assert policy.allow_rerank is True
        assert policy.allow_embeddings is True
        assert policy.allow_local_llm is False
    
    def test_policy_custom(self):
        """Кастомная политика."""
        policy = GPUPolicy(
            enabled=False,
            allow_local_llm=True,
        )
        
        assert policy.enabled is False
        assert policy.allow_local_llm is True


class TestGPUDetector:
    """Tests for GPUDetector."""
    
    def test_cuda_not_available(self):
        """CUDA недоступен."""
        detector = GPUDetector()
        detector._cuda_available = False
        assert detector.cuda_available is False
        
    def test_cuda_available_mocked(self):
        """CUDA доступен (mocked)."""
        detector = GPUDetector()
        detector._cuda_available = True
        assert detector.cuda_available is True
    
    def test_get_gpus_no_cuda(self):
        """Получение GPU без CUDA."""
        detector = GPUDetector()
        detector._cuda_available = False
        
        gpus = detector.get_gpus()
        assert gpus == []
    
    def test_get_primary_gpu(self):
        """Получение основного GPU."""
        detector = GPUDetector()
        detector._cuda_available = True
        detector._gpus = [
            GPUInfo(index=0, name="GPU1", total_memory_gb=8.0),
            GPUInfo(index=1, name="GPU2", total_memory_gb=16.0),
        ]
        
        gpu = detector.get_primary_gpu()
        assert gpu.name == "GPU1"
    
    def test_get_primary_gpu_none(self):
        """Нет GPU."""
        detector = GPUDetector()
        detector._cuda_available = False
        
        gpu = detector.get_primary_gpu()
        assert gpu is None


class TestGPUPolicyManager:
    """Tests for GPUPolicyManager."""
    
    def test_manager_defaults(self):
        """Политика по умолчанию."""
        manager = GPUPolicyManager()
        
        assert manager.policy.enabled is True
        assert manager.policy.allow_local_llm is False
    
    def test_can_use_gpu_disabled_policy(self):
        """Политика отключена."""
        manager = GPUPolicyManager(GPUPolicy(enabled=False))
        manager.detector._cuda_available = False
        
        assert manager.can_use_gpu_for("transcription") is False
        assert manager.can_use_gpu_for("rerank") is False

    def test_can_use_gpu_no_cuda(self):
        """CUDA недоступен."""
        manager = GPUPolicyManager()
        manager.detector._cuda_available = False
        
        assert manager.can_use_gpu_for("transcription") is False
    
    def test_can_use_gpu_insufficient_memory(self):
        """Недостаточно памяти."""
        manager = GPUPolicyManager()
        manager.detector._cuda_available = True
        manager.detector._gpus = [GPUInfo(index=0, name="Weak GPU", total_memory_gb=3.0)]
        
        # 3GB - 2GB reserved = 1GB доступно (80% = 0.8GB)
        # transcription требует 4GB - не хватит
        assert manager.can_use_gpu_for("transcription") is False
        
        # rerank требует 2GB - не хватит
        assert manager.can_use_gpu_for("rerank") is False

    def test_can_use_gpu_sufficient_memory(self):
        """Достаточно памяти."""
        manager = GPUPolicyManager(GPUPolicy(allow_local_llm=True))  # Включаем local_llm
        manager.detector._cuda_available = True
        manager.detector._gpus = [GPUInfo(index=0, name="Strong GPU", total_memory_gb=16.0)]
        
        # Хватит для всего
        assert manager.can_use_gpu_for("transcription") is True
        assert manager.can_use_gpu_for("rerank") is True
        assert manager.can_use_gpu_for("embeddings") is True
        
        # local_llm требует 8GB
        assert manager.can_use_gpu_for("local_llm") is True
    
    def test_can_use_gpu_flag_disabled(self):
        """Флаг разрешения отключен."""
        manager = GPUPolicyManager(GPUPolicy(allow_transcription=False))
        manager.detector._cuda_available = True
        manager.detector._gpus = [GPUInfo(index=0, name="GPU", total_memory_gb=16.0)]
        
        assert manager.can_use_gpu_for("transcription") is False
        assert manager.can_use_gpu_for("rerank") is True
    
    def test_get_device_for_task(self):
        """Получение устройства для задачи."""
        manager = GPUPolicyManager(GPUPolicy(allow_local_llm=True))
        manager.detector._cuda_available = True
        manager.detector._gpus = [GPUInfo(index=0, name="GPU", total_memory_gb=16.0)]
        
        assert manager.get_device_for("transcription") == "cuda"
        assert manager.get_device_for("unknown") == "cpu"
    
    def test_get_device_for_task_cpu_fallback(self):
        """Fallback на CPU."""
        manager = GPUPolicyManager(GPUPolicy(enabled=False))
        manager.detector._cuda_available = False
        
        assert manager.get_device_for("transcription") == "cpu"
    
    def test_get_compute_type_for_task(self):
        """Получение типа вычислений."""
        manager = GPUPolicyManager()
        manager.detector._cuda_available = True
        manager.detector._gpus = [GPUInfo(index=0, name="GPU", total_memory_gb=16.0)]
        
        assert manager.get_compute_type_for("transcription") == "float16"
    
    def test_get_compute_type_cpu(self):
        """CPU compute type."""
        manager = GPUPolicyManager()
        manager.detector._cuda_available = False
        
        assert manager.get_compute_type_for("transcription") == "int8"
    
    def test_get_policy_status(self):
        """Получение статуса политики."""
        manager = GPUPolicyManager()
        manager.detector._cuda_available = True
        manager.detector._gpus = [GPUInfo(index=0, name="Test GPU", total_memory_gb=8.0)]
        
        status = manager.get_policy_status()
        
        assert status["cuda_available"] is True
        assert status["gpu"]["name"] == "Test GPU"
        assert status["gpu"]["total_memory_gb"] == 8.0
        assert status["policy"]["enabled"] is True
        assert "can_use_gpu" in status
    
    def test_update_policy(self):
        """Обновление политики."""
        manager = GPUPolicyManager()
        
        manager.update_policy({
            "enabled": False,
            "allow_local_llm": True,
            "reserved_memory_gb": 4.0,
        })
        
        assert manager.policy.enabled is False
        assert manager.policy.allow_local_llm is True
        assert manager.policy.reserved_memory_gb == 4.0


class TestGPUPolicyIntegration:
    """Integration tests for GPU policy."""
    
    def test_convenience_functions(self):
        """Конvenience функции."""
        # Mock manager
        with patch("app.gpu.policy.gpu_policy_manager") as mock_manager:
            mock_manager.get_device_for.return_value = "cuda"
            mock_manager.can_use_gpu_for.return_value = True
            
            assert get_device_for_task("transcription") == "cuda"
            assert can_use_gpu("transcription") is True


class TestGPURealWorldScenarios:
    """Real-world GPU scenarios."""
    
    def test_weak_gpu_single_card(self):
        """Слабый GPU (4GB)."""
        manager = GPUPolicyManager()
        manager.detector._cuda_available = True
        manager.detector._gpus = [GPUInfo(index=0, name="GTX 1650", total_memory_gb=4.0)]
        
        # 4GB - 2GB reserved = 2GB доступно (80% = 1.6GB)
        # transcription требует 4GB - не хватит
        assert manager.can_use_gpu_for("transcription") is False
        
        # rerank и embeddings требуют 2GB - не хватит
        assert manager.can_use_gpu_for("rerank") is False
        assert manager.can_use_gpu_for("embeddings") is False

        # Не хватит для local_llm
        assert manager.can_use_gpu_for("local_llm") is False
    
    def test_strong_gpu_dual_card(self):
        """Сильные GPU (2x RTX 3090)."""
        manager = GPUPolicyManager(GPUPolicy(allow_local_llm=True))
        manager.detector._cuda_available = True
        manager.detector._gpus = [
            GPUInfo(index=0, name="RTX 3090", total_memory_gb=24.0),
            GPUInfo(index=1, name="RTX 3090", total_memory_gb=24.0),
        ]
        
        # Хватит для всего
        assert manager.can_use_gpu_for("transcription") is True
        assert manager.can_use_gpu_for("rerank") is True
        assert manager.can_use_gpu_for("embeddings") is True
        assert manager.can_use_gpu_for("local_llm") is True
    
    def test_no_gpu_system(self):
        """Система без GPU."""
        manager = GPUPolicyManager()
        manager.detector._cuda_available = False
        
        assert manager.get_device_for("transcription") == "cpu"
        assert manager.get_device_for("rerank") == "cpu"
        assert manager.get_device_for("embeddings") == "cpu"
        assert manager.get_device_for("local_llm") == "cpu"
    
    def test_user_disabled_gpu(self):
        """Пользователь отключил GPU."""
        manager = GPUPolicyManager(GPUPolicy(enabled=False))
        manager.detector._cuda_available = True
        manager.detector._gpus = [GPUInfo(index=0, name="RTX 3080", total_memory_gb=10.0)]
        
        # Всё на CPU несмотря на наличие GPU
        assert manager.get_device_for("transcription") == "cpu"
        assert manager.can_use_gpu_for("rerank") is False
