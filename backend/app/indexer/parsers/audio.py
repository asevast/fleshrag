import os
import subprocess
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.router import ModelRouter

# Директория для временных файлов
TMP_DIR = Path("/tmp/rag_audio")
TMP_DIR.mkdir(exist_ok=True)

# Кэш для локальной модели faster-whisper
_local_model_cache: dict[str, "WhisperModel"] = {}


def _get_local_model(model_size: str = "base") -> "WhisperModel":
    """Загружает локальную модель faster-whisper (кешируется)."""
    import torch
    from faster_whisper import WhisperModel
    
    key = f"{model_size}_int8"
    if key not in _local_model_cache:
        # Автоматическое определение устройства: GPU если доступен
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        print(f"faster-whisper using device: {device}, compute_type: {compute_type}")
        _local_model_cache[key] = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _local_model_cache[key]


def to_wav(src_path: str) -> str:
    """
    Конвертирует любой аудио/видео файл в 16 kHz моно WAV через ffmpeg.
    Возвращает путь к временному WAV файлу.
    """
    out = TMP_DIR / f"{uuid.uuid4()}.wav"
    result = subprocess.run(
        [
            "ffmpeg", "-i", src_path,
            "-vn",               # без видеодорожки
            "-ar", "16000",      # 16 kHz — требование Whisper
            "-ac", "1",          # моно
            "-c:a", "pcm_s16le", # несжатый WAV
            "-y",                # перезаписать если существует
            "-loglevel", "warning"
        ],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        # Проверка: есть ли вообще аудиодорожка
        check = subprocess.run(
            ["ffmpeg", "-i", src_path],
            capture_output=True,
            text=True
        )
        if "Audio: none" in check.stderr or "no audio" in check.stderr.lower():
            raise RuntimeError(f"Файл {src_path} не содержит аудиодорожки")
        raise RuntimeError(f"ffmpeg failed for {src_path}: {result.stderr[:500]}")
    return str(out)


def transcribe_cloud(audio_path: str, router: "ModelRouter") -> str:
    """Транскрибация через cloud whisper-1 (neuraldeep.ru)."""
    with open(audio_path, "rb") as f:
        result = router.get_client().audio.transcriptions.create(
            model="whisper-1", file=f
        )
    return result.text


def transcribe_local(audio_path: str) -> str:
    """Транскрибация через local faster-whisper (base INT8)."""
    model = _get_local_model("base")
    segments, _ = model.transcribe(
        audio_path,
        language="ru",
        beam_size=3,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500}
    )
    return " ".join(s.text.strip() for s in segments)


def transcribe_audio(audio_path: str, router: "ModelRouter") -> str:
    """
    Транскрибирует аудио файл, используя текущий провайдер из роутера.
    cloud: whisper-1 через neuraldeep.ru
    local: faster-whisper base INT8
    """
    return router.transcribe_audio(audio_path)


def parse_audio(src_path: str, router: "ModelRouter") -> str:
    """
    Полный пайплайн для аудиофайла:
    1. Конвертация в 16kHz mono WAV через ffmpeg
    2. Транскрибация (cloud/local)
    3. Удаление временного файла
    """
    wav_path = to_wav(src_path)
    try:
        return transcribe_audio(wav_path, router)
    finally:
        if os.path.exists(wav_path):
            os.unlink(wav_path)