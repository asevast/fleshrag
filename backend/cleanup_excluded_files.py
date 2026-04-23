#!/usr/bin/env python3
"""
Скрипт для удаления из базы данных файлов с игнорируемыми расширениями.
Удаляет записи из SQLite и точки из Qdrant.
"""

import os
import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.config import settings
from app.db.models import SessionLocal, IndexedFile
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue

# Игнорируемые расширения (синхронизировано с backend/app/indexer/watcher.py)
IGNORE_EXTS = {".wc", ".torrent", ".!ut", ".ini", ".dmg", ".deb", ".dat", ".exe", ".dll", ".bin", ".iso", ".img", ".tmp", ".lock", ".log", ".db", ".sqlite", ".sqlite3", ".pyc", ".pyo", ".so", ".dylib", ".parts", ""}

def cleanup_excluded_files():
    db = SessionLocal()
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    COLLECTION_NAME = "multimodal_rag"
    
    try:
        # Получаем все файлы из базы
        files = db.query(IndexedFile).all()
        print(f"Найдено файлов в базе: {len(files)}")
        
        excluded_count = 0
        deleted_files = []
        
        for file in files:
            ext = Path(file.path).suffix.lower()
            if ext in IGNORE_EXTS:
                excluded_count += 1
                deleted_files.append(file.path)
                
                # Удаляем из Qdrant
                try:
                    qdrant.delete(
                        collection_name=COLLECTION_NAME,
                        points_selector=Filter(
                            must=[FieldCondition(key="path", match=MatchValue(value=file.path))]
                        ),
                        wait=True
                    )
                    print(f"✓ Удалено из Qdrant: {file.path}")
                except Exception as e:
                    print(f"✗ Ошибка удаления из Qdrant {file.path}: {e}")
                
                # Удаляем из SQLite
                try:
                    db.delete(file)
                    db.commit()
                except Exception as e:
                    print(f"✗ Ошибка удаления из SQLite {file.path}: {e}")
                    db.rollback()
        
        print(f"\n=== Итог ===")
        print(f"Всего файлов в базе: {len(files)}")
        print(f"Удалено исключённых файлов: {excluded_count}")
        print(f"Осталось файлов: {len(files) - excluded_count}")
        
    finally:
        db.close()

if __name__ == "__main__":
    print("Запуск очистки базы от файлов с игнорируемыми расширениями...")
    cleanup_excluded_files()