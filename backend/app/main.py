from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

from app.api import search, files, index, settings, models, conversations, export
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
app.include_router(settings.router, prefix="/api")
app.include_router(models.router, prefix="/api")
app.include_router(conversations.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# Запуск watchdog в отдельном потоке при старте приложения
@app.on_event("startup")
def on_startup():
    watchdog_thread = threading.Thread(target=run_watchdog_forever, daemon=True)
    watchdog_thread.start()
