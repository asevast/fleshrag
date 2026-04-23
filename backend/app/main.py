from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading
from sqlalchemy import text
from qdrant_client import QdrantClient

from app.api import admin, search, files, index, settings as settings_api, models, conversations, export
from app.config import settings
from app.db.models import SessionLocal, IndexPath
from app.db.crud import add_index_path
from app.indexer.watchdog_service import run_watchdog_forever

app = FastAPI(title="Multimodal RAG", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(search.router, prefix="/api")
app.include_router(files.router, prefix="/api")
app.include_router(index.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(admin.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/ready")
async def ready():
    checks: dict[str, str] = {}

    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
    finally:
        db.close()

    try:
        qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        qdrant.get_collections()
        checks["qdrant"] = "ok"
    except Exception as exc:
        checks["qdrant"] = f"error: {exc}"

    provider_ready = "cloud-configured" if settings.neuraldeep_api_key else "local-fallback"
    checks["provider"] = provider_ready

    is_ready = all(not value.startswith("error:") for value in checks.values())
    return {"status": "ready" if is_ready else "degraded", "checks": checks}


# Инициализация путей индексации из .env при первом запуске
def init_index_paths():
    db = SessionLocal()
    try:
        # Добавляем путь из .env если БД пуста
        paths = db.query(IndexPath).all()
        if not paths:
            for path in settings.index_paths.split(":"):
                if path:
                    add_index_path(db, path)
    finally:
        db.close()


# Запуск watchdog в отдельном потоке при старте приложения
@app.on_event("startup")
def on_startup():
    init_index_paths()
    watchdog_thread = threading.Thread(target=run_watchdog_forever, daemon=True)
    watchdog_thread.start()
