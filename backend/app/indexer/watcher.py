import os
import hashlib
from datetime import datetime

from app.db.models import SessionLocal
from app.db.crud import create_or_update_file, get_file_by_path
from app.indexer.parsers.pdf import parse_pdf
from app.indexer.parsers.office import parse_docx, parse_xlsx, parse_pptx, parse_txt
from app.indexer.parsers.audio import parse_audio
from app.indexer.parsers.image import parse_image
from app.indexer.parsers.video import parse_video
from app.indexer.chunker import chunk_text
from app.indexer.embedder import embed_and_upsert


IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode", "dist", "build", ".pytest_cache", ".mypy_cache"}
IGNORE_EXTS = {"", ".exe", ".dll", ".bin", ".iso", ".img", ".tmp", ".lock", ".log", ".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".so", ".dylib"}

# Статические расширения по типам
TEXT_EXTS = {".txt", ".md", ".py", ".js", ".ts", ".jsx", ".tsx", ".json", ".yaml", ".yml", ".csv", ".html", ".htm", ".xml", ".css", ".scss", ".less", ".sh", ".bat", ".ps1", ".sql", ".cpp", ".c", ".h", ".hpp", ".java", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".r", ".lua", ".pl", ".dockerfile", ".ini", ".cfg", ".toml", ".env", ".gitignore", ".gitattributes"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus", ".oga"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".svg", ".ico"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"}
OFFICE_EXTS = {".docx", ".xlsx", ".pptx"}


def file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def should_ignore(file_path: str) -> bool:
    parts = file_path.split(os.sep)
    if any(ignored in parts for ignored in IGNORE_DIRS):
        return True
    ext = os.path.splitext(file_path)[1].lower()
    if ext in IGNORE_EXTS:
        return True
    return False


def index_directory(path: str):
    for root, _, files in os.walk(path):
        for filename in files:
            file_path = os.path.join(root, filename)
            if should_ignore(file_path):
                continue
            try:
                index_single_file(file_path)
            except Exception as e:
                print(f"Error indexing {file_path}: {e}")


def extract_text(file_path: str, ext: str) -> str:
    if ext == ".pdf":
        return parse_pdf(file_path)
    elif ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".xlsx":
        return parse_xlsx(file_path)
    elif ext == ".pptx":
        return parse_pptx(file_path)
    elif ext in TEXT_EXTS:
        return parse_txt(file_path)
    elif ext in AUDIO_EXTS:
        return parse_audio(file_path)
    elif ext in IMAGE_EXTS:
        return parse_image(file_path)
    elif ext in VIDEO_EXTS:
        return parse_video(file_path)
    else:
        # Fallback: markitdown если доступен
        try:
            from markitdown import MarkItDown
            md = MarkItDown()
            result = md.convert(file_path)
            return result.text_content
        except Exception:
            return ""


def index_single_file(file_path: str):
    db = SessionLocal()
    try:
        ext = os.path.splitext(file_path)[1].lower()
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        fhash = file_hash(file_path)

        existing = create_or_update_file(db, file_path, os.path.basename(file_path), fhash, ext, mtime)
        if existing and existing.status == "indexed" and existing.file_hash == fhash:
            return  # Файл не изменился — пропускаем

        text = extract_text(file_path, ext)

        if text is None:
            text = ""

        if not text.strip():
            create_or_update_file(db, file_path, os.path.basename(file_path), fhash, ext, mtime, status="empty")
            return

        chunks = chunk_text(text)
        embed_and_upsert(chunks, file_path, os.path.basename(file_path), ext)
        create_or_update_file(db, file_path, os.path.basename(file_path), fhash, ext, mtime, chunk_count=len(chunks), status="indexed")
    except Exception as e:
        create_or_update_file(db, file_path, os.path.basename(file_path), "", ext, datetime.utcnow(), status="error", error_message=str(e))
        raise
    finally:
        db.close()
