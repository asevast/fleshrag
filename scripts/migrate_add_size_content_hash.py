"""
Миграция: Добавление полей size_bytes и content_hash в таблицу indexed_files

Выполнить:
    python scripts/migrate_add_size_content_hash.py
"""

import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, text, inspect
from app.config import settings
from app.db.models import Base, IndexedFile

def migrate():
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    
    # Получаем список существующих колонок
    columns = [col['name'] for col in inspector.get_columns('indexed_files')]
    
    print("📊 Текущие колонки в indexed_files:")
    for col in columns:
        print(f"  - {col}")
    
    # Добавляем size_bytes если нет
    if 'size_bytes' not in columns:
        print("\n➕ Добавляем колонку: size_bytes INTEGER")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE indexed_files ADD COLUMN size_bytes INTEGER DEFAULT 0"))
            conn.commit()
        print("✅ size_bytes добавлена")
    else:
        print("\n✅ size_bytes уже существует")
    
    # Добавляем content_hash если нет
    if 'content_hash' not in columns:
        print("\n➕ Добавляем колонку: content_hash VARCHAR")
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE indexed_files ADD COLUMN content_hash VARCHAR"))
            conn.commit()
        print("✅ content_hash добавлена")
    else:
        print("\n✅ content_hash уже существует")
    
    print("\n✅ Миграция завершена!")
    
    # Проверяем результат
    columns = [col['name'] for col in inspector.get_columns('indexed_files')]
    print("\n📊 Итоговые колонки:")
    for col in columns:
        print(f"  - {col}")


if __name__ == "__main__":
    migrate()
