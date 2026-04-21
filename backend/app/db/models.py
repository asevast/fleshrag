import os
import datetime
import json
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Убедимся, что директория для БД существует (для Windows и Linux)
db_path = settings.database_url.replace("sqlite:///", "")
DB_DIR = str(Path(db_path).parent)
if DB_DIR and not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

engine = create_engine(settings.database_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class IndexedFile(Base):
    __tablename__ = "indexed_files"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, nullable=False, index=True)
    filename = Column(String, nullable=False, index=True)
    file_hash = Column(String, nullable=False)
    file_type = Column(String, nullable=False)
    mtime = Column(DateTime, nullable=False)
    chunk_count = Column(Integer, default=0)
    status = Column(String, default="pending")  # pending, indexed, error, empty
    error_message = Column(Text, nullable=True)
    indexed_at = Column(DateTime, default=datetime.datetime.utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
