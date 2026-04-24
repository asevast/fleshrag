import os
import hashlib
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import SessionLocal
from app.db.crud import create_or_update_file, get_file_by_path
from app.indexer.parsers.pdf import parse_pdf
from app.indexer.parsers.office import parse_docx, parse_xlsx, parse_pptx, parse_txt
from app.indexer.parsers.audio import parse_audio
from app.indexer.parsers.image import parse_image
from app.indexer.parsers.video import parse_video
from app.indexer.parsers.code import parse_code, parse_code_simple
from app.indexer.parsers.markitdown import parse_markitdown
from app.indexer.chunker import chunk_text
from app.indexer.embedder import embed_and_upsert
from app.indexer import bm25

# Инициализация BM25 индекса при загрузке
bm25.get_bm25_index()


IGNORE_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".idea", ".vscode", "dist", "build", ".pytest_cache", ".mypy_cache"}
IGNORE_EXTS = {"", ".exe", ".dll", ".bin", ".iso", ".img", ".tmp", ".lock", ".log", ".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".so", ".dylib"}

# Статические расширения по типам
TEXT_EXTS = {".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".html", ".htm", ".xml", ".css", ".scss", ".less", ".sh", ".bat", ".ps1", ".sql", ".dockerfile", ".ini", ".cfg", ".toml", ".env", ".gitignore", ".gitattributes"}
CODE_EXTS = {".py", ".js", ".ts", ".jsx", ".tsx", ".cpp", ".c", ".h", ".hpp", ".java", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".r", ".lua", ".pl"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".wma", ".opus", ".oga"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tiff", ".tif", ".webp", ".svg", ".ico"}
VIDEO_EXTS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg", ".3gp"}
OFFICE_EXTS = {".docx", ".xlsx", ".pptx"}
PDF_EXTS = {".pdf"}


def file_hash(path: str) -> str:
    """Вычисляет MD5 хэш содержимого файла."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def content_fingerprint(path: str, file_hash: str, mtime: datetime, size_bytes: int) -> str:
    """
    Вычисляет SHA256 fingerprint для идемпотентной индексации.
    
    Fingerprint включает:
    - file_hash: MD5 содержимого
    - mtime: время модификации
    - size_bytes: размер файла
    
    Это гарантирует стабильность chunk_id при переиндексации.
    """
    content = f"{file_hash}_{mtime.timestamp()}_{size_bytes}"
    return hashlib.sha256(content.encode()).hexdigest()


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
    if ext in PDF_EXTS:
        return parse_pdf(file_path)
    elif ext == ".docx":
        return parse_docx(file_path)
    elif ext == ".xlsx":
        return parse_xlsx(file_path)
    elif ext == ".pptx":
        return parse_pptx(file_path)
    elif ext in TEXT_EXTS:
        return parse_txt(file_path)
    elif ext in CODE_EXTS:
        # Для кода используем AST-парсинг, затем собираем чанки
        chunks = parse_code(file_path)
        return "\n\n".join([c.get("code", "") for c in chunks])
    elif ext in AUDIO_EXTS:
        return parse_audio(file_path)
    elif ext in IMAGE_EXTS:
        return parse_image(file_path)
    elif ext in VIDEO_EXTS:
        return parse_video(file_path)
    else:
        # Fallback: markitdown для остальных форматов
        return parse_markitdown(file_path)


def index_single_file(file_path: str, db: Optional[Session] = None):
    """Индексирует один файл. Идемпотентная индексация с fingerprint."""
    own_session = db is None
    if own_session:
        db = SessionLocal()
    try:
        ext = os.path.splitext(file_path)[1].lower()
        mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        size_bytes = os.path.getsize(file_path)
        fhash = file_hash(file_path)

        # Вычисляем fingerprint для идемпотентности
        fingerprint = content_fingerprint(file_path, fhash, mtime, size_bytes)

        existing = get_file_by_path(db, file_path)
        
        # Проверяем, нужно ли переиндексировать
        if existing and existing.status == "indexed":
            if existing.file_hash == fhash and existing.size_bytes == size_bytes:
                # Файл не изменился — пропускаем
                return
        
        # Для новых файлов или изменившихся — полная индексация
        # Удаляем старые чанки из Qdrant
        from app.indexer.embedder import delete_file_chunks
        delete_file_chunks(file_path)

        text = extract_text(file_path, ext)

        if text is None:
            text = ""

        if not text.strip():
            create_or_update_file(
                db, file_path, os.path.basename(file_path), fhash, ext, mtime,
                size_bytes=size_bytes, content_hash=fingerprint, status="empty"
            )
            return

        chunks = chunk_text(text)
        
        # Передаём file_hash для генерации стабильных chunk_id
        embed_and_upsert(chunks, file_path, os.path.basename(file_path), ext, fhash)
        
        create_or_update_file(
            db, file_path, os.path.basename(file_path), fhash, ext, mtime,
            size_bytes=size_bytes, content_hash=fingerprint, chunk_count=len(chunks), status="indexed"
        )
    except Exception as e:
        create_or_update_file(
            db, file_path, os.path.basename(file_path), "", ext, datetime.utcnow(),
            size_bytes=size_bytes if 'size_bytes' in locals() else 0,
            status="error", error_message=str(e)
        )
        raise
    finally:
        if own_session:
            db.close()
