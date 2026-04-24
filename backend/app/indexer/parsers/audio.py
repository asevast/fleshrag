import os
import tempfile
import hashlib
from faster_whisper import WhisperModel

from app.cache.artifacts import artifact_cache

PARSER_VERSION = "1.0"


# Глобальный кэш моделей: модель создаётся один раз на размер
_model_cache: dict[str, WhisperModel] = {}


def _get_model(model_size: str = "tiny") -> WhisperModel:
    if model_size not in _model_cache:
        _model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model_cache[model_size]


def _compute_content_hash(path: str) -> str:
    """Вычисляет хэш содержимого файла."""
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:32]


def transcribe_audio(path: str, model_size: str = "tiny") -> str:
    """Транскрибация аудио с кэшированием результата."""
    content_hash = _compute_content_hash(path)
    
    # Проверяем кэш
    cached = artifact_cache.get(content_hash, "transcription", PARSER_VERSION)
    if cached is not None:
        return cached
    
    # Выполняем транскрибацию
    model = _get_model(model_size)
    segments, _ = model.transcribe(path, language="ru", condition_on_previous_text=False)
    text = " ".join([segment.text for segment in segments])
    
    # Сохраняем в кэш
    artifact_cache.set(text, "transcription", PARSER_VERSION)
    
    return text


def parse_audio(path: str) -> str:
    return transcribe_audio(path)
