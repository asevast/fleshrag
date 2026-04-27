from __future__ import annotations

from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.db import crud
from app.db.models import TokenLog, get_db
from app.models import ModelRouter
from app.services.settings_service import SettingsService
from app.tasks.celery_app import index_directory_task
from app.gpu.policy import gpu_policy_manager

router = APIRouter()


@router.get("/admin/settings")
async def get_admin_settings(db: Session = Depends(get_db)):
    service = SettingsService(db)
    return {
        "active_provider": service.get_active_provider(),
        "llm_model": service.get_llm_model(),
        "embed_model": service.get_embed_model(),
        "rerank_model": service.get_rerank_model(),
        "llm_temperature": service.get_temperature(),
        "llm_max_tokens": service.get_max_tokens(),
        "chunk_size": service.get_chunk_size(),
        "chunk_overlap": service.get_chunk_overlap(),
        "top_k_search": service.get_top_k_search(),
        "top_k_rerank": service.get_top_k_rerank(),
        "index_paths": service.get_index_paths(),
    }


@router.put("/admin/settings")
async def update_admin_settings(payload: dict, db: Session = Depends(get_db)):
    service = SettingsService(db)
    allowed_keys = {
        "active_provider",
        "llm_model",
        "embed_model",
        "rerank_model",
        "llm_temperature",
        "llm_max_tokens",
        "chunk_size",
        "chunk_overlap",
        "top_k_search",
        "top_k_rerank",
        "index_paths",
    }
    for key, value in payload.items():
        if key not in allowed_keys:
            continue
        if key == "index_paths":
            service.set_index_paths(value)
        else:
            crud.set_setting(db, key, str(value))
    return await get_admin_settings(db)


@router.get("/admin/status")
async def get_admin_status(db: Session = Depends(get_db)):
    router_instance = ModelRouter(db)
    provider = router_instance.get_provider()
    stats = crud.get_index_stats(db)
    
    # Получаем информацию о версии индекса
    try:
        from app.indexer.embedder import COLLECTION_NAME, _get_index_metadata, _get_current_embed_model, _get_vector_dimension
        from qdrant_client import QdrantClient
        qdrant_admin = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            timeout=10.0,  # Увеличенный таймаут для медленных запросов
        )
        
        metadata = _get_index_metadata() if qdrant_admin.collection_exists(COLLECTION_NAME) else None
        
        index_version_info = {
            "has_metadata": metadata is not None,
            "embed_model": metadata.get("embed_model") if metadata else None,
            "vector_dim": metadata.get("vector_dim") if metadata else None,
            "index_version": metadata.get("index_version") if metadata else None,
            "current_model": _get_current_embed_model(),
            "current_dim": _get_vector_dimension(),
        }
    except Exception as e:
        index_version_info = {
            "has_metadata": False,
            "error": f"Request timed out or unavailable: {str(e)}",
        }
    
    # Получаем runtime state
    runtime_status = router_instance.get_runtime_status()
    
    # Получаем GPU status
    gpu_status = gpu_policy_manager.get_policy_status()
    
    return {
        "provider": provider.capabilities.provider,
        "models": {
            "llm": provider.capabilities.llm_model,
            "embed": provider.capabilities.embed_model,
            "rerank": provider.capabilities.rerank_model,
        },
        "index": {
            "is_indexing": stats.get("pending", 0) > 0,
            "stats": stats,
        },
        "index_version": index_version_info,
        "services": [
            {"name": "backend", "status": "running", "detail": "FastAPI active"},
            {"name": "qdrant", "status": "running", "detail": f"{settings.qdrant_host}:{settings.qdrant_port}"},
            {"name": "redis", "status": "running", "detail": settings.redis_url},
            {"name": "provider", "status": "running", "detail": provider.capabilities.provider},
        ],
        "circuit_breaker": router_instance.circuit_breaker.get_status(),
        "runtime_state": runtime_status,
        "gpu": gpu_status,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/admin/budget/stats")
async def get_budget_stats(db: Session = Depends(get_db)):
    today = datetime.utcnow().date()
    start_today = datetime.combine(today, datetime.min.time())
    week_ago = start_today - timedelta(days=6)

    rows = (
        db.query(
            func.date(TokenLog.ts).label("day"),
            func.sum(TokenLog.cost_usd).label("cost_usd"),
            func.sum(TokenLog.input_tok).label("input_tok"),
            func.sum(TokenLog.output_tok).label("output_tok"),
        )
        .filter(TokenLog.ts >= week_ago)
        .group_by(func.date(TokenLog.ts))
        .order_by(func.date(TokenLog.ts))
        .all()
    )

    day_rows = (
        db.query(
            TokenLog.op_type,
            func.sum(TokenLog.cost_usd).label("cost_usd"),
            func.sum(TokenLog.input_tok).label("input_tok"),
            func.sum(TokenLog.output_tok).label("output_tok"),
        )
        .filter(TokenLog.ts >= start_today)
        .group_by(TokenLog.op_type)
        .all()
    )

    today_cost = sum(float(row.cost_usd or 0.0) for row in day_rows)
    return {
        "daily_limit_usd": 1.0,
        "today_cost_usd": today_cost,
        "today_ratio": today_cost / 1.0 if today_cost else 0.0,
        "last_7_days": [
            {
                "day": str(row.day),
                "cost_usd": float(row.cost_usd or 0.0),
                "input_tok": int(row.input_tok or 0),
                "output_tok": int(row.output_tok or 0),
            }
            for row in rows
        ],
        "breakdown": [
            {
                "op_type": row.op_type,
                "cost_usd": float(row.cost_usd or 0.0),
                "input_tok": int(row.input_tok or 0),
                "output_tok": int(row.output_tok or 0),
            }
            for row in day_rows
        ],
    }


@router.post("/admin/index/reindex-all")
async def admin_reindex_all():
    indexed_paths = settings.get_index_paths()
    for path in indexed_paths:
        index_directory_task.delay(path)
    return {
        "status": "queued",
        "paths": indexed_paths,
        "count": len(indexed_paths),
    }


@router.post("/admin/models/test")
async def test_models_connection(db: Session = Depends(get_db)):
    provider = ModelRouter(db).get_provider()
    started = datetime.utcnow()
    try:
        provider.list_models()
        latency_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
        return {
            "status": "ok",
            "provider": provider.capabilities.provider,
            "latency_ms": latency_ms,
            "llm_model": provider.capabilities.llm_model,
            "embed_model": provider.capabilities.embed_model,
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@router.get("/admin/models/catalog")
async def get_models_catalog(db: Session = Depends(get_db)):
    service = SettingsService(db)
    active_provider = service.get_active_provider()
    catalog = {
        "active_provider": active_provider,
        "cloud": {
            "llm": [settings.cloud_llm_model, settings.cloud_llm_economy_model],
            "embed": [settings.cloud_embed_model, settings.cloud_embed_alt_model],
            "rerank": [settings.cloud_rerank_model],
        },
        "local": {
            "llm": [],
            "embed": [],
            "rerank": [settings.local_rerank_model],
        },
    }
    try:
        local_models = ModelRouter(db).get_provider("local").list_models()
        catalog["local"]["llm"] = [m["name"] for m in local_models if "embed" not in m["name"]]
        catalog["local"]["embed"] = [m["name"] for m in local_models if "embed" in m["name"]]
    except httpx.HTTPError:
        catalog["local"]["llm"] = [settings.local_llm_model]
        catalog["local"]["embed"] = [settings.local_embed_model]
    
    # Добавляем multilingual-e5-large через embed-service в локальные embed модели
    # Проверяем доступность embed-service через settings
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{settings.embed_service_url}/health", timeout=3.0)
            if resp.status_code == 200:
                if "multilingual-e5-large" not in catalog["local"]["embed"]:
                    catalog["local"]["embed"].append("multilingual-e5-large")
        except (httpx.HTTPError, httpx.ConnectError, httpx.TimeoutException):
            pass  # embed-service недоступен, не добавляем в каталог
    return catalog
