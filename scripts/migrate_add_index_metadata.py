"""
Миграция: Создание таблицы index_metadata для версионирования индекса

Выполнить:
    python scripts/migrate_add_index_metadata.py
"""

import sys
from pathlib import Path

# Добавляем backend в path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import create_engine, text, inspect
from app.config import settings
from app.db.models import Base, IndexMetadata

def migrate():
    engine = create_engine(settings.database_url)
    inspector = inspect(engine)
    
    # Проверяем существует ли таблица
    table_names = inspector.get_table_names()
    
    print("📊 Существующие таблицы:")
    for table in table_names:
        print(f"  - {table}")
    
    if 'index_metadata' in table_names:
        print("\n✅ Таблица index_metadata уже существует")
    else:
        print("\n➕ Создаём таблицу: index_metadata")
        IndexMetadata.__table__.create(engine)
        print("✅ index_metadata создана")
    
    # Проверяем результат
    table_names = inspector.get_table_names()
    print("\n📊 Итоговые таблицы:")
    for table in table_names:
        print(f"  - {table}")
    
    print("\n✅ Миграция завершена!")
    
    # Показываем структуру новой таблицы
    if 'index_metadata' in table_names:
        columns = inspector.get_columns('index_metadata')
        print("\n📋 Структура index_metadata:")
        for col in columns:
            print(f"  - {col['name']}: {col['type']}")


if __name__ == "__main__":
    migrate()
