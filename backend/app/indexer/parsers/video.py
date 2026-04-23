import os
import subprocess
import uuid
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.router import ModelRouter

from app.indexer.parsers.audio import to_wav, transcribe_audio
from app.indexer.parsers.image import parse_images_batch

# Директория для временных файлов
TMP_DIR = Path("/tmp/rag_video")
TMP_DIR.mkdir(exist_ok=True)


def extract_frames(video_path: str, fps: float = 1.0) -> list[str]:
    """
    Извлекает кадры из видео для визуального анализа (OCR).
    Возвращает список путей к временным JPG файлам.
    """
    out_dir = TMP_DIR / f"frames_{uuid.uuid4()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    subprocess.run(
        [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps={fps}",   # извлекать fps кадров в секунду
            "-q:v", "3",            # качество JPEG (2-5 хорошее)
            "-y",
            "-loglevel", "error"
        ] + [str(out_dir / "frame_%04d.jpg")],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    return sorted(str(p) for p in out_dir.glob("*.jpg"))


def process_media_file(file_path: str, router: "ModelRouter") -> str:
    """
    Полный пайплайн для любого медиафайла (аудио или видео):
    1. Если видео → извлечь аудиодорожку + кадры
    2. Ресемплировать аудио в 16kHz mono WAV
    3. Транскрибировать (cloud whisper-1 / local faster-whisper)
    4. Для кадров → OCR через EasyOCR
    5. Удалить временные файлы
    """
    from app.indexer.parsers.video import extract_frames_from_video
    
    lines = []
    temp_files = []
    
    try:
        # Проверка типа файла
        ext = Path(file_path).suffix.lower()
        is_video = ext in {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm"}
        
        if is_video:
            # 1. Аудиодорожка из видео
            wav_path = to_wav(file_path)
            temp_files.append(wav_path)
            
            # 2. Транскрибация аудио
            transcript = transcribe_audio(wav_path, router)
            if transcript.strip():
                lines.append("[Аудио-транскрипция]\n" + transcript)
            
            # 3. Извлечение кадров
            frames = extract_frames_from_video(file_path, fps=0.2)  # 1 кадр в 5 сек
            if frames:
                # Сэмплируем не более 10 кадров равномерно
                if len(frames) > 10:
                    step = len(frames) // 10
                    frames = frames[::step][:10]
                
                # OCR на кадрах
                ocr_results = parse_images_batch(frames)
                for i, ocr_text in enumerate(ocr_results):
                    if ocr_text.strip():
                        lines.append(f"\n[Кадр {i+1} OCR]\n" + ocr_text)
                
                # Очистка кадров
                for frame_path in frames:
                    try:
                        os.unlink(frame_path)
                    except:
                        pass
        else:
            # Просто аудиофайл
            wav_path = to_wav(file_path)
            temp_files.append(wav_path)
            transcript = transcribe_audio(wav_path, router)
            if transcript.strip():
                lines.append("[Аудио-транскрипция]\n" + transcript)
        
        return "\n".join(lines)
    
    finally:
        # Очистка временных файлов
        for f in temp_files:
            try:
                os.unlink(f)
            except:
                pass


# Для обратной совместимости
def parse_video(video_path: str, router: "ModelRouter", max_frames_ocr: int = 10) -> str:
    """Устаревший интерфейс — используйте process_media_file."""
    return process_media_file(video_path, router)


def extract_frames_from_video(video_path: str, fps: float = 1.0) -> list[str]:
    """Извлекает кадры из видео (обёртка над extract_frames)."""
    return extract_frames(video_path, fps)