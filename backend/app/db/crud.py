from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import IndexedFile


def get_file_by_path(db: Session, path: str):
    return db.query(IndexedFile).filter(IndexedFile.path == path).first()


def create_or_update_file(db: Session, path: str, filename: str, file_hash: str, file_type: str, mtime, chunk_count: int = 0, status: str = "pending", error_message: str = None):
    file = get_file_by_path(db, path)
    if file:
        file.file_hash = file_hash
        file.mtime = mtime
        file.chunk_count = chunk_count
        file.status = status
        file.error_message = error_message
    else:
        file = IndexedFile(
            path=path,
            filename=filename,
            file_hash=file_hash,
            file_type=file_type,
            mtime=mtime,
            chunk_count=chunk_count,
            status=status,
            error_message=error_message,
        )
        db.add(file)
    db.commit()
    db.refresh(file)
    return file


def get_indexed_files(db: Session, skip: int = 0, limit: int = 100):
    return db.query(IndexedFile).offset(skip).limit(limit).all()


def get_index_stats(db: Session) -> dict:
    counts = db.query(
        IndexedFile.status,
        func.count(IndexedFile.id)
    ).group_by(IndexedFile.status).all()
    total = db.query(func.count(IndexedFile.id)).scalar()
    stats = {status: count for status, count in counts}
    stats["total"] = total or 0
    stats.setdefault("indexed", 0)
    stats.setdefault("pending", 0)
    stats.setdefault("error", 0)
    stats.setdefault("empty", 0)
    return stats
