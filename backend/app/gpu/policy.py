"""
GPU Auto-detect и Policy Layer.

Автоматическое определение доступных GPU и распределение задач:
- transcription: может использовать GPU для ускорения
- reranker: может использовать GPU
- embeddings: может использовать GPU
- local LLM: не использовать GPU на слабых картах

Флаг в admin/settings для управления GPU policy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class GPUInfo:
    """Информация о GPU."""
    index: int
    name: str
    total_memory_gb: float
    available: bool = True


@dataclass
class GPUPolicy:
    """Политика использования GPU."""
    enabled: bool = True
    reserved_memory_gb: float = 2.0  # Резервируем память для системы
    max_usage_percent: float = 0.8   # Не использовать больше 80% памяти
    
    # Разрешить GPU для конкретных задач
    allow_transcription: bool = True
    allow_rerank: bool = True
    allow_embeddings: bool = True
    allow_local_llm: bool = False  # По умолчанию False для слабых GPU
    
    # Минимальный объём памяти для различных задач
    min_memory_for_transcription_gb: float = 4.0
    min_memory_for_rerank_gb: float = 2.0
    min_memory_for_embeddings_gb: float = 2.0
    min_memory_for_local_llm_gb: float = 8.0


class GPUDetector:
    """Автоопределение GPU и информации о них."""
    
    def __init__(self):
        self._cuda_available = None
        self._gpus: list[GPUInfo] | None = None
    
    @property
    def cuda_available(self) -> bool:
        """Проверяет доступность CUDA."""
        if self._cuda_available is None:
            try:
                import torch
                self._cuda_available = torch.cuda.is_available()
            except Exception as e:
                logger.warning(f"CUDA недоступен: {e}")
                self._cuda_available = False
        return self._cuda_available
    
    def get_gpus(self) -> list[GPUInfo]:
        """Возвращает список доступных GPU."""
        if self._gpus is not None:
            return self._gpus
        
        self._gpus = []
        
        if not self.cuda_available:
            return self._gpus
        
        try:
            import torch
            
            gpu_count = torch.cuda.device_count()
            for i in range(gpu_count):
                name = torch.cuda.get_device_name(i)
                total_memory = torch.cuda.get_device_properties(i).total_memory / (1024 ** 3)
                
                gpu = GPUInfo(
                    index=i,
                    name=name,
                    total_memory_gb=round(total_memory, 2),
                )
                self._gpus.append(gpu)
            
            logger.info(f"Найдено GPU: {len(self._gpus)}")
            for gpu in self._gpus:
                logger.info(f"  GPU {gpu.index}: {gpu.name} ({gpu.total_memory_gb} GB)")
        
        except Exception as e:
            logger.error(f"Ошибка при получении информации о GPU: {e}")
        
        return self._gpus
    
    def get_primary_gpu(self) -> GPUInfo | None:
        """Возвращает основной GPU."""
        gpus = self.get_gpus()
        return gpus[0] if gpus else None


class GPUPolicyManager:
    """Менеджер GPU policy."""
    
    def __init__(self, policy: GPUPolicy | None = None):
        self.detector = GPUDetector()
        self.policy = policy or GPUPolicy()
        self._primary_gpu: GPUInfo | None = None
        self._can_use_gpu_for: dict[str, bool] = {}
    
    def _check_gpu_requirements(self, task_type: str) -> bool:
        """Проверяет что GPU удовлетворяет требованиям для задачи."""
        if not self.policy.enabled or not self.detector.cuda_available:
            return False
        
        # Получаем основной GPU
        gpu = self.detector.get_primary_gpu()
        if not gpu:
            return False
        
        # Определяем минимальные требования
        if task_type == "transcription":
            min_memory = self.policy.min_memory_for_transcription_gb
            allow_flag = self.policy.allow_transcription
        elif task_type == "rerank":
            min_memory = self.policy.min_memory_for_rerank_gb
            allow_flag = self.policy.allow_rerank
        elif task_type == "embeddings":
            min_memory = self.policy.min_memory_for_embeddings_gb
            allow_flag = self.policy.allow_embeddings
        elif task_type == "local_llm":
            min_memory = self.policy.min_memory_for_local_llm_gb
            allow_flag = self.policy.allow_local_llm
        else:
            return False
        
        if not allow_flag:
            return False
        
        # Проверяем память
        available_memory = gpu.total_memory_gb - self.policy.reserved_memory_gb
        max_usable = available_memory * self.policy.max_usage_percent
        
        return max_usable >= min_memory
    
    def can_use_gpu_for(self, task_type: str) -> bool:
        """
        Проверяет можно ли использовать GPU для задачи.
        
        Args:
            task_type: Тип задачи (transcription, rerank, embeddings, local_llm)
        
        Returns:
            True если GPU можно использовать
        """
        # Кэшируем результат
        if task_type not in self._can_use_gpu_for:
            self._can_use_gpu_for[task_type] = self._check_gpu_requirements(task_type)
        
        return self._can_use_gpu_for[task_type]
    
    def get_device_for(self, task_type: str) -> str:
        """
        Возвращает устройство для задачи.
        
        Args:
            task_type: Тип задачи
        
        Returns:
            "cuda" или "cpu"
        """
        if self.can_use_gpu_for(task_type):
            return "cuda"
        return "cpu"
    
    def get_compute_type_for(self, task_type: str) -> str:
        """
        Возвращает тип вычислений для задачи.
        
        Args:
            task_type: Тип задачи
        
        Returns:
            compute type для faster-whisper или других моделей
        """
        if self.can_use_gpu_for(task_type):
            return "float16"
        return "int8"
    
    def get_policy_status(self) -> dict:
        """Возвращает статус GPU policy."""
        gpu = self.detector.get_primary_gpu()
        
        return {
            "cuda_available": self.detector.cuda_available,
            "gpu": {
                "name": gpu.name if gpu else None,
                "total_memory_gb": gpu.total_memory_gb if gpu else None,
            },
            "policy": {
                "enabled": self.policy.enabled,
                "reserved_memory_gb": self.policy.reserved_memory_gb,
                "max_usage_percent": self.policy.max_usage_percent,
            },
            "can_use_gpu": {
                "transcription": self.can_use_gpu_for("transcription"),
                "rerank": self.can_use_gpu_for("rerank"),
                "embeddings": self.can_use_gpu_for("embeddings"),
                "local_llm": self.can_use_gpu_for("local_llm"),
            },
        }
    
    def update_policy(self, policy_updates: dict) -> None:
        """
        Обновляет policy из settings.
        
        Args:
            policy_updates: Словарь с обновлениями
        """
        if "enabled" in policy_updates:
            self.policy.enabled = policy_updates["enabled"]
            self._can_use_gpu_for.clear()  # Сброс кэша
        
        if "reserved_memory_gb" in policy_updates:
            self.policy.reserved_memory_gb = policy_updates["reserved_memory_gb"]
            self._can_use_gpu_for.clear()
        
        if "allow_transcription" in policy_updates:
            self.policy.allow_transcription = policy_updates["allow_transcription"]
            self._can_use_gpu_for.clear()
        
        if "allow_rerank" in policy_updates:
            self.policy.allow_rerank = policy_updates["allow_rerank"]
            self._can_use_gpu_for.clear()
        
        if "allow_embeddings" in policy_updates:
            self.policy.allow_embeddings = policy_updates["allow_embeddings"]
            self._can_use_gpu_for.clear()
        
        if "allow_local_llm" in policy_updates:
            self.policy.allow_local_llm = policy_updates["allow_local_llm"]
            self._can_use_gpu_for.clear()


# Глобальный экземпляр
gpu_policy_manager = GPUPolicyManager()


def get_device_for_task(task_type: str) -> str:
    """
    Convenience функция для получения устройства.
    
    Args:
        task_type: Тип задачи
    
    Returns:
        "cuda" или "cpu"
    """
    return gpu_policy_manager.get_device_for(task_type)


def can_use_gpu(task_type: str) -> bool:
    """
    Convenience функция для проверки GPU.
    
    Args:
        task_type: Тип задачи
    
    Returns:
        True если GPU можно использовать
    """
    return gpu_policy_manager.can_use_gpu_for(task_type)


# Примеры использования в коде

def configure_whisper_for_gpu():
    """Конфигурирует Whisper для использования GPU если доступно."""
    device = get_device_for_task("transcription")
    compute_type = gpu_policy_manager.get_compute_type_for("transcription")
    
    return {
        "device": device,
        "compute_type": compute_type,
    }


def configure_reranker_for_gpu():
    """Конфигурирует reranker для использования GPU если доступно."""
    device = get_device_for_task("rerank")
    
    return {
        "device": device,
    }


def configure_embeddings_for_gpu():
    """Конфигурирует embeddings для использования GPU если доступно."""
    device = get_device_for_task("embeddings")
    
    return {
        "device": device,
    }


def configure_local_llm_for_gpu():
    """Конфигурирует local LLM для использования GPU если доступно."""
    device = get_device_for_task("local_llm")
    
    return {
        "device": device,
    }
