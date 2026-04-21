from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.models import get_db
from app.db.crud import get_indexed_files

router = APIRouter()


@router.get("/files")
async def list_files(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    files = get_indexed_files(db, skip=skip, limit=limit)
    return [{"id": f.id, "path": f.path, "filename": f.filename, "status": f.status, "indexed_at": f.indexed_at} for f in files]
