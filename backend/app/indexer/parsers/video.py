import os
import tempfile
import av
from PIL import Image as PILImage

from app.indexer.parsers.audio import transcribe_audio
from app.indexer.parsers.image import parse_images_batch


def extract_audio_from_video(video_path: str) -> str:
    container = av.open(video_path)
    audio_stream = next((s for s in container.streams if s.type == "audio"), None)
    if not audio_stream:
        return ""

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        output = av.open(tmp.name, "w")
        out_stream = output.add_stream("pcm_s16le", rate=16000)
        out_stream.channels = 1

        for packet in container.demux(audio_stream):
            for frame in packet.decode():
                frame.pts = None
                frame.rate = 16000
                frame = frame.resample(16000, "mono", "s16")
                for packet in out_stream.encode(frame):
                    output.mux(packet)

        output.close()
        container.close()
        return tmp.name


def extract_frames_from_video(video_path: str, fps: float = 1.0) -> list:
    container = av.open(video_path)
    video_stream = next((s for s in container.streams if s.type == "video"), None)
    if not video_stream:
        return []

    frames = []
    frame_interval = 1.0 / fps
    last_time = -1.0

    for packet in container.demux(video_stream):
        for frame in packet.decode():
            current_time = float(frame.pts * frame.time_base)
            if current_time - last_time >= frame_interval:
                last_time = current_time
                img = frame.to_image()
                frames.append(img)

    container.close()
    return frames


def parse_video(path: str, max_frames_ocr: int = 5) -> str:
    """Транскрибирует аудио + выполняет OCR на ключевых кадрах видео."""
    lines = []

    # 1. Аудио
    audio_path = extract_audio_from_video(path)
    if audio_path:
        try:
            transcript = transcribe_audio(audio_path, model_size="tiny")
            if transcript.strip():
                lines.append("[Аудио-транскрипция]\n" + transcript)
        finally:
            os.unlink(audio_path)

    # 2. OCR на кадрах (сэмплируем равномерно, не больше max_frames_ocr)
    try:
        frames = extract_frames_from_video(path, fps=0.2)  # 1 кадр в 5 сек
        if frames:
            # Сэмплируем кадры равномерно
            if len(frames) > max_frames_ocr:
                step = len(frames) // max_frames_ocr
                frames = frames[::step][:max_frames_ocr]

            with tempfile.TemporaryDirectory() as tmpdir:
                frame_paths = []
                for i, img in enumerate(frames):
                    fp = os.path.join(tmpdir, f"frame_{i:03d}.png")
                    img.save(fp)
                    frame_paths.append(fp)

                ocr_results = parse_images_batch(frame_paths)
                for i, ocr_text in enumerate(ocr_results):
                    if ocr_text.strip():
                        lines.append(f"\n[Кадр {i+1} OCR]\n" + ocr_text)
    except Exception:
        pass

    return "\n".join(lines)

