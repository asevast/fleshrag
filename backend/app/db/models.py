import os
import datetime
import json
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, event
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.engine import Engine

from app.config import settings

# Убедимся, что директория для БД существует (для Windows и Linux)
db_path = settings.database_url.replace("sqlite:///", "")
DB_DIR = str(Path(db_path).parent)
if DB_DIR and not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR, exist_ok=True)

# SQLite hardening для concurrent access
# https://www.sqlite.org/wal.html
SQLITE_CONNECT_ARGS = {
    "check_same_thread": False,  # Разрешить использование в разных потоках
    "timeout": 5000,  # busy_timeout: ждать 5 секунд вместо немедленной ошибки
}

engine = create_engine(
    settings.database_url,
    connect_args=SQLITE_CONNECT_ARGS,
    # Дополнительные настройки для производительности
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=3600,   # Пересоздавать соединения через час
)

# Включаем WAL (Write-Ahead Logging) режим для лучшей конкурентности
# Это позволяет читателям не блокировать писателей и наоборот
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Настраивает SQLite pragma при каждом подключении."""
    cursor = dbapi_connection.cursor()
    
    # Включаем WAL режим для лучшей конкурентности
    cursor.execute("PRAGMA journal_mode=WAL")
    
    # Устанавливаем busy timeout (дублирование connect_args для надёжности)
    cursor.execute("PRAGMA busy_timeout=5000")
    
    # Включаем foreign keys (по умолчанию в SQLite выключены)
    cursor.execute("PRAGMA foreign_keys=ON")
    
    # Оптимизация для SSD (если используется)
    cursor.execute("PRAGMA synchronous=NORMAL")
    
    # Кэширование страниц (2000 страниц по 4KB = 8MB кэш)
    cursor.execute("PRAGMA cache_size=-2000")
    
    # Включаем поддержку memory-mapped I/O (256MB)
    cursor.execute("PRAGMA mmap_size=268435456")
    
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class IndexedFile(Base):
    __tablename__ = "indexed_files"

    id = Column(Integer, primary_key=True, index=True)
    path = Column(String, unique=True, index=True)
    filename = Column(String, nullable=False, index=True)
    file_hash = Column(String, nullable=False)  # MD5 от содержимого файла
    file_type = Column(String, nullable=False)
    mtime = Column(DateTime, nullable=False)
    size_bytes = Column(Integer, default=0)  # Размер файла в байтах
    chunk_count = Column(Integer, default=0)
    content_hash = Column(String, nullable=True)  # SHA256 fingerprint для идемпотентности
    status = Column(String, default="pending")  # pending, indexed, error, empty
    error_message = Column(Text, nullable=True)
    indexed_at = Column(DateTime, default=datetime.datetime.utcnow)


class IndexMetadata(Base):
    """
    Метаданные векторного индекса для отслеживания версии и совместимости.
    
    Хранит информацию о модели эмбеддингов, размерности векторов и версии индекса.
    При смене модели требуется переиндексация.
    """
    __tablename__ = "index_metadata"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)  # embed_model, vector_dim, index_version
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class AppSetting(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class TokenLog(Base):
    __tablename__ = "token_logs"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, index=True)
    model = Column(String, nullable=False)
    op_type = Column(String, nullable=False, index=True)
    input_tok = Column(Integer, default=0)
    output_tok = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    meta_json = Column(Text, nullable=True)
    ts = Column(DateTime, default=datetime.datetime.utcnow, index=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    sources = Column(Text, nullable=True)  # JSON-список источников
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    conversation = relationship("Conversation", back_populates="messages")


Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
