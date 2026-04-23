import json
from datetime import datetime
from typing import List, Optional, Dict, Any, AsyncGenerator, Tuple

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import settings
from app.indexer.embedder import COLLECTION_NAME
from app.indexer import bm25
from app.models import ModelRouter
from app.rag.reranker import rerank
from app.services.settings_service import SettingsService

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

# Коэффициенты для гибридного поиска
DENSE_WEIGHT = 0.7
BM25_WEIGHT = 0.3


def _build_qdrant_filter(filters: Optional[dict] = None) -> Optional[qdrant_models.Filter]:
    """Преобразует фильтры из запроса в Qdrant Filter."""
    if not filters:
        return None
    
    conditions = []
    
    # Фильтр по типам файлов
    if filters.get("file_types"):
        conditions.append(
            qdrant_models.FieldCondition(
                key="file_type",
                match=qdrant_models.MatchAny(any=filters["file_types"]),
            )
        )
    
    # Фильтр по дате (mtime в payload)
    if filters.get("date_after"):
        try:
            date_after = datetime.fromisoformat(filters["date_after"].replace("Z", "+00:00"))
            conditions.append(
                qdrant_models.FieldCondition(
                    key="mtime",
                    range=qdrant_models.Range(gte=date_after.timestamp()),
                )
            )
        except (ValueError, AttributeError):
            pass
    
    if filters.get("date_before"):
        try:
            date_before = datetime.fromisoformat(filters["date_before"].replace("Z", "+00:00"))
            conditions.append(
                qdrant_models.FieldCondition(
                    key="mtime",
                    range=qdrant_models.Range(lte=date_before.timestamp()),
                )
            )
        except (ValueError, AttributeError):
            pass
    
    # Фильтр по пути (содержит подстроку)
    if filters.get("path_contains"):
        conditions.append(
            qdrant_models.FieldCondition(
                key="path",
                match=qdrant_models.MatchText(text=filters["path_contains"]),
            )
        )
    
    return qdrant_models.Filter(must=conditions) if conditions else None


async def search_query(query: str, top_k: int = None, filters: Optional[dict] = None, use_hybrid: bool = True) -> List[Dict[str, Any]]:
    """
    Гибридный поиск: BM25 + dense embeddings с reciprocal rank fusion.
    """
    runtime_settings = SettingsService()
    top_k = top_k or runtime_settings.get_top_k_search()
    provider = ModelRouter().get_provider()
    
    qdrant_filter = _build_qdrant_filter(filters)
    
    # 1. Dense поиск (векторы)
    embedding = provider.embed_text(query)
    dense_results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=embedding,
        limit=top_k * 2,  # Берём больше для fusion
        query_filter=qdrant_filter,
        with_payload=True,
    ).points
    
    # 2. BM25 поиск (текст)
    bm25_results = []
    if use_hybrid:
        bm25_matches = bm25.search_bm25(query, top_k=top_k * 2)
        # Для BM25 нужно получить payload из Qdrant по ID
        for doc_id, score in bm25_matches:
            # doc_id имеет формат "{path}_{chunk_index}"
            # Извлекаем путь
            parts = doc_id.rsplit('_', 1)
            if len(parts) == 2:
                path = parts[0]
                # Ищем в Qdrant по path
                try:
                    found = qdrant.scroll(
                        collection_name=COLLECTION_NAME,
                        scroll_filter=qdrant_models.Filter(
                            must=[{"key": "path", "match": {"value": path}}]
                        ),
                        limit=5,
                        with_payload=True,
                        with_vectors=False,
                    )[0]
                    for point in found:
                        bm25_results.append({
                            "path": point.payload.get("path", ""),
                            "filename": point.payload.get("filename", ""),
                            "snippet": point.payload.get("text", "")[:500],
                            "score": score,
                            "page": point.payload.get("page"),
                            "file_type": point.payload.get("file_type"),
                            "_id": point.id,
                        })
                except Exception:
                    pass
    
    # 3. Reciprocal Rank Fusion
    if use_hybrid and bm25_results:
        return _reciprocal_rank_fusion(dense_results, bm25_results, top_k)
    else:
        # Только dense
        results = []
        for point in dense_results[:top_k]:
            payload = point.payload or {}
            results.append({
                "path": payload.get("path", ""),
                "filename": payload.get("filename", ""),
                "snippet": payload.get("text", "")[:500],
                "score": point.score,
                "page": payload.get("page"),
                "file_type": payload.get("file_type"),
            })
        return results


def _reciprocal_rank_fusion(dense_results, bm25_results: List[Dict], top_k: int) -> List[Dict[str, Any]]:
    """
    Reciprocal Rank Fusion для объединения dense и BM25 результатов.
    """
    # Нормализуем dense результаты
    dense_ranked = []
    for i, point in enumerate(dense_results):
        payload = point.payload or {}
        dense_ranked.append({
            "path": payload.get("path", ""),
            "filename": payload.get("filename", ""),
            "snippet": payload.get("text", "")[:500],
            "dense_score": point.score,
            "bm25_score": 0.0,
            "page": payload.get("page"),
            "file_type": payload.get("file_type"),
        })
    
    # Словарь для fusion по path
    fused: Dict[str, Dict] = {}
    
    # Добавляем dense результаты
    for i, item in enumerate(dense_ranked):
        key = item["path"]
        if key not in fused:
            fused[key] = item
            fused[key]["_dense_rank"] = i + 1
    
    # Добавляем BM25 результаты
    for i, item in enumerate(bm25_results):
        key = item["path"]
        if key in fused:
            fused[key]["bm25_score"] = item["score"]
            fused[key]["_bm25_rank"] = i + 1
        else:
            fused[key] = {
                "path": item["path"],
                "filename": item["filename"],
                "snippet": item["snippet"],
                "dense_score": 0.0,
                "bm25_score": item["score"],
                "page": item.get("page"),
                "file_type": item.get("file_type"),
                "_bm25_rank": i + 1,
            }
    
    # Вычисляем финальный score
    for item in fused.values():
        dense_rank = item.get("_dense_rank", len(dense_ranked) + 1)
        bm25_rank = item.get("_bm25_rank", len(bm25_results) + 1)
        
        # Reciprocal Rank Fusion formula
        item["score"] = (
            DENSE_WEIGHT / (dense_rank + 60) +
            BM25_WEIGHT / (bm25_rank + 60)
        )
    
    # Сортируем по финальному score
    sorted_results = sorted(fused.values(), key=lambda x: x["score"], reverse=True)
    
    # Убираем служебные поля
    results = []
    for item in sorted_results[:top_k]:
        results.append({
            "path": item["path"],
            "filename": item["filename"],
            "snippet": item["snippet"],
            "score": item["score"],
            "page": item.get("page"),
            "file_type": item.get("file_type"),
        })
    
    return results


async def _build_rag_context(query: str, top_k: int = None) -> tuple[str, List[Dict]]:
    """Выполняет поиск + reranking и возвращает контекст + источники."""
    runtime_settings = SettingsService()
    top_k = top_k or runtime_settings.get_top_k_rerank()
    search_results = await search_query(query, top_k=runtime_settings.get_top_k_search())
    reranked = rerank(query, search_results, top_k=top_k)
    context = "\n\n".join([f"[{i+1}] {r['snippet']}" for i, r in enumerate(reranked)])
    return context, reranked


def _build_prompt(context: str, query: str) -> str:
    return f"""Ответь на вопрос пользователя, используя только предоставленный контекст. Если ответа нет в контексте, скажи об этом.

Контекст:
{context}

Вопрос: {query}

Ответ:"""


async def ask_query(query: str, top_k: int = None, filters: Optional[dict] = None) -> Dict[str, Any]:
    context, sources = await _build_rag_context(query, top_k=top_k)
    prompt = _build_prompt(context, query)
    provider = ModelRouter().get_provider()
    response = provider.complete(prompt, system_prompt="Ты — RAG ассистент по локальным файлам.")
    return {
        "answer": response,
        "sources": [{"path": r["path"], "filename": r["filename"], "snippet": r["snippet"], "score": r["score"], "rerank_score": r.get("rerank_score")} for r in sources],
    }


async def ask_query_stream(query: str, top_k: int = None, filters: Optional[dict] = None) -> AsyncGenerator[str, None]:
    """SSE-стриминг ответа LLM. Первым идёт JSON с источниками, затем токены ответа."""
    try:
        context, sources = await _build_rag_context(query, top_k=top_k)
        prompt = _build_prompt(context, query)
        provider = ModelRouter().get_provider()

        # Отправляем источники первым событием
        sources_payload = {
            "type": "sources",
            "sources": [{"path": r["path"], "filename": r["filename"], "snippet": r["snippet"], "score": r["score"], "rerank_score": r.get("rerank_score")} for r in sources],
        }
        yield f"data: {json.dumps(sources_payload, ensure_ascii=False)}\n\n"

        # Стриминг токенов от LLM
        for token in provider.stream_complete(prompt, system_prompt="Ты — RAG ассистент по локальным файлам."):
            payload = {"type": "token", "content": token}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"
    except Exception as e:
        error_payload = {"type": "error", "message": str(e)}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
