import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.config import settings
from app.tasks.celery_app import index_file_task
from app.indexer.watcher import should_ignore
from app.db.models import SessionLocal
from app.db.crud import get_index_paths


TEMP_EXTS = {"", ".tmp", ".temp", ".swp", ".swo", ".crdownload", ".part", ".download", ".json5"}
IGNORE_PATH_PREFIXES = {"/tmp", "/var/tmp"}


def get_indexed_paths_from_db() -> list:
    """Получает список путей индексации из БД."""
    try:
        db = SessionLocal()
        paths = get_index_paths(db, active_only=True)
        db.close()
        return [p.path for p in paths]
    except Exception:
        # Fallback на переменную окружения
        return [p for p in settings.index_paths.split(":") if p]


class IndexEventHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and self._should_index(event.src_path):
            self._schedule(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._should_index(event.src_path):
            self._schedule(event.src_path)

    def on_moved(self, event):
        if not event.is_directory and self._should_index(event.dest_path):
            self._schedule(event.dest_path)

    def _should_index(self, path: str) -> bool:
        # Игнорим файлы во временных директориях
        for prefix in IGNORE_PATH_PREFIXES:
            if path.startswith(prefix):
                return False
        # Игнорим временные файлы и файлы по стандартному списку
        ext = os.path.splitext(path)[1].lower()
        if ext in TEMP_EXTS:
            return False
        return not should_ignore(path)

    def _schedule(self, path: str):
        # Проверяем, что файл внутри индексируемых директорий из БД
        indexed_paths = get_indexed_paths_from_db()
        for indexed_path in indexed_paths:
            if path.startswith(indexed_path):
                index_file_task.delay(path)
                break


def start_watchdog(paths: list):
    observer = Observer()
    handler = IndexEventHandler()
    scheduled = 0
    for path in paths:
        if os.path.isdir(path):
            observer.schedule(handler, path, recursive=True)
            scheduled += 1
    if scheduled == 0:
        return None
    observer.start()
    return observer


def run_watchdog_forever():
    # Получаем пути из БД (или из env если БД пуста)
    paths = get_indexed_paths_from_db()
    observer = start_watchdog(paths)
    if observer is None:
        return
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
