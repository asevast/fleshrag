import os
import mimetypes
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.models import get_db, IndexedFile
from app.db.crud import get_indexed_files, get_file_by_path, get_available_file_types

router = APIRouter()

PREVIEW_MAX_BYTES = 256 * 1024  # 256 KB


@router.get("/files")
async def list_files(
    skip: int = 0,
    limit: int = 100,
    file_types: Optional[str] = Query(None, description="Comma-separated file types"),
    status: Optional[str] = Query(None, description="Filter by status"),
    path_contains: Optional[str] = Query(None, description="Filter by path substring"),
    db: Session = Depends(get_db)
):
    filters = {}
    if file_types:
        filters["file_types"] = [ft.strip() for ft in file_types.split(",")]
    if status:
        filters["status"] = status
    if path_contains:
        filters["path_contains"] = path_contains
    
    files = get_indexed_files(db, skip=skip, limit=limit, filters=filters if filters else None)
    return [{"id": f.id, "path": f.path, "filename": f.filename, "status": f.status, "file_type": f.file_type, "indexed_at": f.indexed_at.isoformat() if f.indexed_at else None} for f in files]


@router.get("/files/types")
async def list_file_types(db: Session = Depends(get_db)):
    return get_available_file_types(db)


@router.get("/files/download")
async def download_file(path: str, db: Session = Depends(get_db)):
    """Скачать файл по пути."""
    # Проверяем, что файл есть в индексе
    file_record = db.query(IndexedFile).filter(IndexedFile.path == path).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found in index")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(path, filename=file_record.filename)


@router.get("/files/preview")
async def preview_file(path: str, db: Session = Depends(get_db)):
    file_record = get_file_by_path(db, path)
    if not file_record:
        raise HTTPException(status_code=404, detail="File not found in index")

    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    mime, _ = mimetypes.guess_type(path)
    mime = mime or "application/octet-stream"

    # Изображения — отдаём как поток
    if mime.startswith("image/"):
        def iter_image():
            with open(path, "rb") as f:
                yield from f
        return StreamingResponse(iter_image(), media_type=mime)

    # Текстовые и office/PDF — читаем текст (с ограничением)
    text_mimes = {
        "text/", "application/json", "application/xml",
        "application/pdf", "application/msword",
        "application/vnd.openxmlformats-officedocument",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
    }
    is_text = any(mime.startswith(tm) for tm in text_mimes) or mime == "application/octet-stream"

    if is_text:
        try:
            size = os.path.getsize(path)
            if size > PREVIEW_MAX_BYTES:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read(PREVIEW_MAX_BYTES)
                content += "\n\n[Файл слишком большой — показано первые 256 КБ]"
                return PlainTextResponse(content)
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return PlainTextResponse(f.read())
        except UnicodeDecodeError:
            raise HTTPException(status_code=400, detail="File appears to be binary")

    raise HTTPException(status_code=400, detail=f"Preview not supported for MIME type: {mime}")
