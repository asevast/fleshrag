"""
Artifact Cache для кэширования результатов OCR, transcription и video frames.

Ключ: content_hash + parser_version
TTL: 30 дней для больших артефактов
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, asdict

from app.config import settings


@dataclass
class ArtifactEntry:
    """Запись кэша артефактов."""
    content_hash: str
    parser_type: str  # ocr, transcription, video_frames
    parser_version: str
    result: Any
    created_at: float
    ttl_seconds: int = 2592000  # 30 дней
    
    @property
    def is_expired(self) -> bool:
        return time.time() > (self.created_at + self.ttl_seconds)
    
    @property
    def cache_key(self) -> str:
        return f"artifact:{self.content_hash}:{self.parser_type}:{self.parser_version}"


class ArtifactCache:
    """
    Кэш для тяжелых артефактов (OCR, транскрипция, видео).
    
    Использует Redis для хранения метаданных и указателей на файлы.
    Сами артефакты хранятся на диске в volumes/artifact_cache/
    """
    
    def __init__(self, cache_dir: str = "./volumes/artifact_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Импортируем redis только при создании
        try:
            import redis
            self.redis = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_timeout=5.0,
            )
            self.redis_available = True
        except Exception:
            self.redis = None
            self.redis_available = False
    
    def _generate_content_hash(self, content: Any) -> str:
        """Генерирует хэш содержимого."""
        if isinstance(content, bytes):
            content_bytes = content
        elif isinstance(content, str):
            content_bytes = content.encode('utf-8')
        else:
            content_bytes = json.dumps(content, sort_keys=True).encode('utf-8')
        
        return hashlib.sha256(content_bytes).hexdigest()[:32]
    
    def get(self, content_hash: str, parser_type: str, parser_version: str) -> Optional[Any]:
        """
        Получает артефакт из кэша.
        
        Returns:
            Результат или None если не найдено/истёк TTL
        """
        cache_key = f"artifact:{content_hash}:{parser_type}:{parser_version}"
        safe_cache_key = cache_key.replace(":", "_")
        
        try:
            if self.redis_available and self.redis:
                # Проверяем метаданные в Redis
                metadata_json = self.redis.get(cache_key)
                if not metadata_json:
                    return None
                
                metadata = json.loads(metadata_json)
                
                # Проверяем TTL
                if time.time() > metadata.get('expires_at', 0):
                    self.redis.delete(cache_key)
                    return None
                
                # Читаем файл с диска
                file_path = self.cache_dir / f"{safe_cache_key}.json"
                if file_path.exists():
                    with open(file_path, 'r', encoding='utf-8') as f:
                        return json.load(f)
            
            # Fallback: проверяем только диск
            file_path = self.cache_dir / f"{safe_cache_key}.json"
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        
        except Exception:
            pass
        
        return None
    
    def set(self, content: Any, parser_type: str, parser_version: str, ttl_seconds: int = 2592000) -> str:
        """
        Сохраняет артефакт в кэш.
        
        Returns:
            content_hash для последующего использования
        """
        content_hash = self._generate_content_hash(content)
        cache_key = f"artifact:{content_hash}:{parser_type}:{parser_version}"
        
        # Для Windows заменяем ':' на '_' в имени файла
        safe_cache_key = cache_key.replace(":", "_")
        
        # Сохраняем на диск
        file_path = self.cache_dir / f"{safe_cache_key}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(content, f, ensure_ascii=False)
        
        # Сохраняем метаданные в Redis
        if self.redis_available and self.redis:
            metadata = {
                'content_hash': content_hash,
                'parser_type': parser_type,
                'parser_version': parser_version,
                'created_at': time.time(),
                'expires_at': time.time() + ttl_seconds,
                'file_path': str(file_path),
            }
            self.redis.setex(
                cache_key,
                ttl_seconds,
                json.dumps(metadata)
            )
        
        return content_hash
    
    def exists(self, content_hash: str, parser_type: str, parser_version: str) -> bool:
        """Проверяет наличие артефакта в кэше."""
        return self.get(content_hash, parser_type, parser_version) is not None
    
    def delete(self, content_hash: str, parser_type: str, parser_version: str) -> bool:
        """Удаляет артефакт из кэша."""
        cache_key = f"artifact:{content_hash}:{parser_type}:{parser_version}"
        safe_cache_key = cache_key.replace(":", "_")
        
        try:
            # Удаляем файл
            file_path = self.cache_dir / f"{safe_cache_key}.json"
            if file_path.exists():
                file_path.unlink()
            
            # Удаляем метаданные
            if self.redis_available and self.redis:
                self.redis.delete(cache_key)
            
            return True
        except Exception:
            return False
    
    def clear(self, parser_type: Optional[str] = None) -> int:
        """
        Очищает кэш.
        
        Args:
            parser_type: Если указан, очищает только этот тип артефактов
        
        Returns:
            Количество удалённых записей
        """
        count = 0
        
        try:
            # Находим все файлы (используем безопасный паттерн)
            pattern = f"artifact_*"
            if parser_type:
                pattern = f"artifact_*_{parser_type}_*"
            
            for file_path in self.cache_dir.glob(f"{pattern}.json"):
                file_path.unlink()
                count += 1
            
            # Очищаем Redis
            if self.redis_available and self.redis:
                redis_pattern = f"artifact:*"
                if parser_type:
                    redis_pattern = f"artifact:*:{parser_type}:*"
                keys = self.redis.keys(redis_pattern)
                if keys:
                    count += self.redis.delete(*keys)
        
        except Exception:
            pass
        
        return count
    
    def get_stats(self) -> dict:
        """Возвращает статистику кэша."""
        total_size = 0
        file_count = 0
        
        try:
            for file_path in self.cache_dir.glob("*.json"):
                total_size += file_path.stat().st_size
                file_count += 1
        except Exception:
            pass
        
        return {
            'file_count': file_count,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'redis_available': self.redis_available,
        }


# Глобальный экземпляр
artifact_cache = ArtifactCache()
