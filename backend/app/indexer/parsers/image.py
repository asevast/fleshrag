import easyocr
import hashlib
from pathlib import Path

from app.cache.artifacts import artifact_cache

PARSER_VERSION = "1.0"

_reader = None


def _get_reader():
    global _reader
    if _reader is None:
        # detail=0 не применяется к Reader, используем detail=0 в readtext
        _reader = easyocr.Reader(["ru", "en"], gpu=False, verbose=False)
    return _reader


def _compute_content_hash(path: str) -> str:
    """Вычисляет хэш содержимого файла."""
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:32]


def parse_image(path: str) -> str:
    """
    OCR изображения с кэшированием результата.
    
    1. Вычисляем content_hash файла
    2. Проверяем кэш
    3. Если нет в кэше — выполняем OCR и сохраняем результат
    """
    content_hash = _compute_content_hash(path)
    
    # Проверяем кэш
    cached = artifact_cache.get(content_hash, "ocr", PARSER_VERSION)
    if cached is not None:
        return cached
    
    # Выполняем OCR
    reader = _get_reader()
    result = reader.readtext(path, detail=0)
    text = "\n".join(result)
    
    # Сохраняем в кэш
    artifact_cache.set(text, "ocr", PARSER_VERSION)
    
    return text


def parse_images_batch(paths: list[str]) -> list[str]:
    """Батчевая OCR для нескольких изображений с кэшированием."""
    reader = _get_reader()
    results = []
    
    for path in paths:
        content_hash = _compute_content_hash(path)
        
        # Проверяем кэш
        cached = artifact_cache.get(content_hash, "ocr", PARSER_VERSION)
        if cached is not None:
            results.append(cached)
            continue
        
        # Выполняем OCR
        result = reader.readtext(path, detail=0)
        text = "\n".join(result)
        
        # Сохраняем в кэш
        artifact_cache.set(text, "ocr", PARSER_VERSION)
        
        results.append(text)
    
    return results

