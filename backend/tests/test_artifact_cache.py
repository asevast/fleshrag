"""Tests for Artifact Cache."""

import pytest
import json
import time
from pathlib import Path
from unittest.mock import Mock

from app.cache.artifacts import ArtifactCache, ArtifactEntry


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Создаёт временную директорию для кэша."""
    return str(tmp_path / "artifact_cache")


@pytest.fixture
def cache(temp_cache_dir):
    """Создаёт ArtifactCache без Redis."""
    cache = ArtifactCache(cache_dir=temp_cache_dir)
    cache.redis_available = False  # Отключаем Redis для тестов
    yield cache


class TestArtifactEntry:
    """Tests for ArtifactEntry dataclass."""
    
    def test_is_expired(self):
        """Проверяет TTL."""
        # Неистёкший
        entry = ArtifactEntry(
            content_hash="abc123",
            parser_type="ocr",
            parser_version="1.0",
            result="test",
            created_at=time.time(),
            ttl_seconds=3600,
        )
        assert entry.is_expired is False
        
        # Истёкший
        entry.created_at = time.time() - 7200  # 2 часа назад
        assert entry.is_expired is True
    
    def test_cache_key(self):
        """Генерирует правильный ключ."""
        entry = ArtifactEntry(
            content_hash="abc123",
            parser_type="ocr",
            parser_version="1.0",
            result="test",
            created_at=time.time(),
        )
        assert entry.cache_key == "artifact:abc123:ocr:1.0"


class TestArtifactCache:
    """Tests for ArtifactCache."""
    
    def test_generate_content_hash_string(self, cache):
        """Генерирует хэш для строки."""
        hash1 = cache._generate_content_hash("test content")
        hash2 = cache._generate_content_hash("test content")
        hash3 = cache._generate_content_hash("different content")
        
        assert hash1 == hash2
        assert hash1 != hash3
        assert len(hash1) == 32
    
    def test_generate_content_hash_bytes(self, cache):
        """Генерирует хэш для байтов."""
        hash1 = cache._generate_content_hash(b"test bytes")
        hash2 = cache._generate_content_hash(b"test bytes")
        
        assert hash1 == hash2
    
    def test_set_and_get(self, cache):
        """Сохраняет и retrieves артефакт."""
        result = {"text": "OCR result", "confidence": 0.95}
        content_hash = cache.set(result, "ocr", "1.0")
        
        retrieved = cache.get(content_hash, "ocr", "1.0")
        assert retrieved == result
    
    def test_exists(self, cache):
        """Проверяет наличие артефакта."""
        content_hash = cache.set("test", "ocr", "1.0")
        
        assert cache.exists(content_hash, "ocr", "1.0") is True
        assert cache.exists("nonexistent", "ocr", "1.0") is False
    
    def test_delete(self, cache):
        """Удаляет артефакт."""
        content_hash = cache.set("test", "ocr", "1.0")
        
        assert cache.exists(content_hash, "ocr", "1.0") is True
        cache.delete(content_hash, "ocr", "1.0")
        assert cache.exists(content_hash, "ocr", "1.0") is False
    
    def test_clear_all(self, cache):
        """Очищает весь кэш."""
        cache.set("test1", "ocr", "1.0")
        cache.set("test2", "transcription", "1.0")
        cache.set("test3", "ocr", "1.0")
        
        count = cache.clear()
        assert count == 3
    
    def test_clear_by_type(self, cache):
        """Очищает кэш по типу."""
        content_hash1 = cache.set("test1", "ocr", "1.0")
        content_hash2 = cache.set("test2", "transcription", "1.0")
        content_hash3 = cache.set("test3", "ocr", "1.0")
        
        count = cache.clear(parser_type="ocr")
        assert count == 2
        assert cache.exists(content_hash1, "ocr", "1.0") is False
        assert cache.exists(content_hash2, "transcription", "1.0") is True
    
    def test_get_stats(self, cache):
        """Возвращает статистику."""
        cache.set("test1", "ocr", "1.0")
        cache.set("test2" * 100, "transcription", "1.0")  # Больший размер
        
        stats = cache.get_stats()
        
        assert stats['file_count'] == 2
        assert stats['total_size_bytes'] > 0
        assert stats['total_size_mb'] >= 0
        assert stats['redis_available'] is False  # Redis отключен в тестах
    
    def test_cache_file_created(self, cache, temp_cache_dir):
        """Проверяет что файл кэша создаётся."""
        content_hash = cache.set("test", "ocr", "1.0")
        cache_key = f"artifact:{content_hash}:ocr:1.0"
        safe_cache_key = cache_key.replace(":", "_")
        
        file_path = Path(temp_cache_dir) / f"{safe_cache_key}.json"
        assert file_path.exists()
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert data == "test"
    

class TestArtifactCacheIntegration:
    """Integration tests for artifact cache workflow."""
    
    def test_ocr_workflow(self, cache):
        """Полный workflow для OCR."""
        # Первый вызов — кэшируем
        content_hash = cache.set("OCR text result", "ocr", "1.0")
        
        # Второй вызов — из кэша
        result = cache.get(content_hash, "ocr", "1.0")
        assert result == "OCR text result"
        
        # Проверяем статистику
        stats = cache.get_stats()
        assert stats['file_count'] == 1
    
    def test_transcription_workflow(self, cache):
        """Полный workflow для транскрипции."""
        # Кэшируем транскрипцию
        content_hash = cache.set("Transcribed audio text", "transcription", "1.0")
        
        # Получаем из кэша
        result = cache.get(content_hash, "transcription", "1.0")
        assert result == "Transcribed audio text"
    
    def test_multiple_parser_types(self, cache):
        """Разные типы парсеров используют разные ключи."""
        ocr_hash = cache.set("OCR result", "ocr", "1.0")
        trans_hash = cache.set("Transcription result", "transcription", "1.0")
        
        # Разные хэши
        assert ocr_hash != trans_hash
        
        # Оба доступны
        assert cache.get(ocr_hash, "ocr", "1.0") == "OCR result"
        assert cache.get(trans_hash, "transcription", "1.0") == "Transcription result"
    
    def test_version_isolation(self, cache):
        """Разные версии парсеров изолированы."""
        hash_v1 = cache.set("Result v1", "ocr", "1.0")
        hash_v2 = cache.set("Result v2", "ocr", "2.0")
        
        # Разные ключи
        assert hash_v1 != hash_v2
        
        # Изолированные результаты
        assert cache.get(hash_v1, "ocr", "1.0") == "Result v1"
        assert cache.get(hash_v2, "ocr", "2.0") == "Result v2"


class TestArtifactCacheEdgeCases:
    """Edge case tests."""
    
    def test_empty_result(self, cache):
        """Кэширует пустой результат."""
        content_hash = cache.set("", "ocr", "1.0")
        result = cache.get(content_hash, "ocr", "1.0")
        assert result == ""
    
    def test_large_result(self, cache):
        """Кэширует большой результат."""
        large_text = "x" * 100000  # 100KB
        content_hash = cache.set(large_text, "ocr", "1.0")
        result = cache.get(content_hash, "ocr", "1.0")
        assert result == large_text
    
    def test_unicode_content(self, cache):
        """Кэширует Unicode содержимое."""
        unicode_text = "Привет мир! 你好世界! مرحبا بالعالم!"
        content_hash = cache.set(unicode_text, "ocr", "1.0")
        result = cache.get(content_hash, "ocr", "1.0")
        assert result == unicode_text
    
    def test_special_characters_in_key(self, cache):
        """Корректно обрабатывает специальные символы в ключе."""
        content_hash = cache.set("test", "video_frames", "1.0-beta")
        result = cache.get(content_hash, "video_frames", "1.0-beta")
        assert result == "test"
