import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from app.config import settings
from app.tasks.celery_app import index_file_task
from app.indexer.watcher import should_ignore


TEMP_EXTS = {"", ".tmp", ".temp", ".swp", ".swo", ".crdownload", ".part", ".download"}


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
        # Игнорим временные файлы и файлы по стандартному списку
        ext = os.path.splitext(path)[1].lower()
        if ext in TEMP_EXTS:
            return False
        return not should_ignore(path)

    def _schedule(self, path: str):
        # Проверяем, что файл внутри индексируемых директорий
        for indexed_path in settings.index_paths.split(":"):
            if path.startswith(indexed_path):
                index_file_task.delay(path)
                break


def start_watchdog(paths: list):
    observer = Observer()
    handler = IndexEventHandler()
    for path in paths:
        if os.path.isdir(path):
            observer.schedule(handler, path, recursive=True)
    observer.start()
    return observer


def run_watchdog_forever():
    paths = settings.index_paths.split(":")
    observer = start_watchdog(paths)
    try:
        while True:
            time.sleep(1)
    finally:
        observer.stop()
        observer.join()
