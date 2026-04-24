from __future__ import annotations

import threading
from datetime import datetime, UTC

import httpx
import redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from qdrant_client import QdrantClient
from sqlalchemy import text

from app.api import admin, conversations, export, files, index, models, search, settings
from app.config import settings as app_settings
from app.db.models import SessionLocal
from app.indexer.watchdog_service import run_watchdog_forever
from app.services.settings_service import SettingsService

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
app.include_router(settings.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


def _check_database() -> str:
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        return "error"
    finally:
        db.close()


def _check_qdrant() -> str:
    try:
        QdrantClient(host=app_settings.qdrant_host, port=app_settings.qdrant_port, timeout=3.0).get_collections()
        return "ok"
    except Exception:
        return "error"


def _check_redis() -> str:
    try:
        redis.from_url(app_settings.redis_url, socket_timeout=3.0).ping()
        return "ok"
    except Exception:
        return "error"


def _check_ollama() -> str:
    try:
        response = httpx.get(f"{app_settings.ollama_host}/api/tags", timeout=3.0)
        return "ok" if response.status_code == 200 else "error"
    except Exception:
        return "error"


def _provider_state() -> str:
    provider = SettingsService().get_active_provider()
    if provider == "cloud":
        return "cloud-configured"
    if provider == "local" and not app_settings.neuraldeep_api_key:
        return "local-fallback"
    return "local-configured"


def _component_snapshot() -> dict[str, str]:
    return {
        "database": _check_database(),
        "qdrant": _check_qdrant(),
        "redis": _check_redis(),
        "ollama": _check_ollama(),
        "provider": _provider_state(),
    }


@app.get("/api/health")
async def health():
    components = _component_snapshot()
    critical_components = ("database", "qdrant", "redis")
    status = "healthy" if all(components[name] == "ok" for name in critical_components) else "degraded"
    return {
        "status": status,
        "components": components,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.get("/api/ready")
async def ready():
    components = _component_snapshot()
    status = "ready" if components["database"] == "ok" and components["qdrant"] == "ok" else "degraded"
    return {"status": status, **components}


@app.on_event("startup")
def on_startup():
    watchdog_thread = threading.Thread(target=run_watchdog_forever, daemon=True)
    watchdog_thread.start()
