import os
import tempfile
from faster_whisper import WhisperModel


# Глобальный кэш моделей: модель создаётся один раз на размер
_model_cache: dict[str, WhisperModel] = {}


def _get_model(model_size: str = "tiny") -> WhisperModel:
    if model_size not in _model_cache:
        _model_cache[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    return _model_cache[model_size]


def transcribe_audio(path: str, model_size: str = "tiny") -> str:
    model = _get_model(model_size)
    segments, _ = model.transcribe(path, language="ru", condition_on_previous_text=False)
    return " ".join([segment.text for segment in segments])


def parse_audio(path: str) -> str:
    return transcribe_audio(path)
