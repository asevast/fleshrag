import json
from datetime import datetime
from typing import Any, AsyncGenerator, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.config import settings
from app.indexer import bm25
from app.indexer.embedder import COLLECTION_NAME
from app.models.router import ModelRouter
from app.rag.reranker import rerank

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
router = ModelRouter()

# Коэффициенты для гибридного поиска
DENSE_WEIGHT = 0.7
BM25_WEIGHT = 0.3


def _build_qdrant_filter(filters: Optional[dict] = None) -> Optional[qdrant_models.Filter]:
    """Преобразует фильтры из запроса в Qdrant Filter."""
    if not filters:
        return None

    conditions = []

    if filters.get("file_types"):
        conditions.append(
            qdrant_models.FieldCondition(
                key="file_type",
                match=qdrant_models.MatchAny(any=filters["file_types"]),
            )
        )

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

    if filters.get("path_contains"):
        conditions.append(
            qdrant_models.FieldCondition(
                key="path",
                match=qdrant_models.MatchText(text=filters["path_contains"]),
            )
        )

    return qdrant_models.Filter(must=conditions) if conditions else None


def _current_provider():
    """Возвращает текущего провайдера с учётом circuit breaker."""
    return router.get_provider()


def _record_provider_success():
    """Записывает успех cloud provider."""
    current = router.get_provider()
    if current.capabilities.provider == "cloud":
        router.record_cloud_success()


def _record_provider_failure():
    """Записывает ошибку cloud provider."""
    current = router.get_provider()
    if current.capabilities.provider == "cloud":
        router.record_cloud_failure()


async def search_query(
    query: str,
    top_k: int = None,
    filters: Optional[dict] = None,
    use_hybrid: bool = True,
) -> List[Dict[str, Any]]:
    """
    Гибридный поиск: BM25 + dense embeddings с reciprocal rank fusion.
    """
    top_k = top_k or settings.top_k_search
    provider = _current_provider()
    qdrant_filter = _build_qdrant_filter(filters)

    embedding = provider.embed_text(query)
    search_result = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=embedding,
        limit=top_k * 2,
        query_filter=qdrant_filter,
        with_payload=True,
    )
    dense_results = search_result.points if hasattr(search_result, "points") else []

    bm25_results = []
    if use_hybrid:
        bm25_matches = bm25.search_bm25(query, top_k=top_k * 2)
        for doc_id, score in bm25_matches:
            parts = doc_id.rsplit("_", 1)
            if len(parts) != 2:
                continue
            path = parts[0]
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
                    bm25_results.append(
                        {
                            "path": point.payload.get("path", ""),
                            "filename": point.payload.get("filename", ""),
                            "snippet": point.payload.get("text", "")[:500],
                            "score": score,
                            "page": point.payload.get("page"),
                            "file_type": point.payload.get("file_type"),
                            "_id": point.id,
                        }
                    )
            except Exception:
                pass

    if use_hybrid and bm25_results:
        return _reciprocal_rank_fusion(dense_results, bm25_results, top_k)

    results = []
    for point in dense_results[:top_k]:
        payload = point.payload or {}
        results.append(
            {
                "path": payload.get("path", ""),
                "filename": payload.get("filename", ""),
                "snippet": payload.get("text", "")[:500],
                "score": point.score,
                "page": payload.get("page"),
                "file_type": payload.get("file_type"),
            }
        )
    return results


def _reciprocal_rank_fusion(
    dense_results,
    bm25_results: List[Dict],
    top_k: int,
) -> List[Dict[str, Any]]:
    dense_ranked = []
    for index, point in enumerate(dense_results):
        payload = point.payload or {}
        dense_ranked.append(
            {
                "path": payload.get("path", ""),
                "filename": payload.get("filename", ""),
                "snippet": payload.get("text", "")[:500],
                "dense_score": point.score,
                "bm25_score": 0.0,
                "page": payload.get("page"),
                "file_type": payload.get("file_type"),
                "_dense_rank": index + 1,
            }
        )

    fused: Dict[str, Dict[str, Any]] = {}

    for item in dense_ranked:
        fused[item["path"]] = item

    for index, item in enumerate(bm25_results):
        key = item["path"]
        if key in fused:
            fused[key]["bm25_score"] = item["score"]
            fused[key]["_bm25_rank"] = index + 1
            continue
        fused[key] = {
            "path": item["path"],
            "filename": item["filename"],
            "snippet": item["snippet"],
            "dense_score": 0.0,
            "bm25_score": item["score"],
            "page": item.get("page"),
            "file_type": item.get("file_type"),
            "_bm25_rank": index + 1,
        }

    for item in fused.values():
        dense_rank = item.get("_dense_rank", len(dense_ranked) + 1)
        bm25_rank = item.get("_bm25_rank", len(bm25_results) + 1)
        item["score"] = (
            DENSE_WEIGHT / (dense_rank + 60)
            + BM25_WEIGHT / (bm25_rank + 60)
        )

    sorted_results = sorted(fused.values(), key=lambda value: value["score"], reverse=True)
    return [
        {
            "path": item["path"],
            "filename": item["filename"],
            "snippet": item["snippet"],
            "score": item["score"],
            "page": item.get("page"),
            "file_type": item.get("file_type"),
        }
        for item in sorted_results[:top_k]
    ]


def _apply_provider_rerank(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int,
) -> List[Dict[str, Any]]:
    provider = _current_provider()
    scores = provider.rerank(query, [doc["snippet"] for doc in documents])
    if not scores:
        return rerank(query, documents, top_k=top_k)

    ranked = []
    for index, document in enumerate(documents):
        ranked.append({**document, "rerank_score": scores[index] if index < len(scores) else 0.0})
    ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
    return ranked[:top_k]


async def _build_rag_context(query: str, top_k: int = None) -> tuple[str, List[Dict]]:
    """Выполняет поиск + reranking и возвращает контекст + источники."""
    top_k = top_k or settings.top_k_rerank
    search_results = await search_query(query, top_k=settings.top_k_search)
    reranked = _apply_provider_rerank(query, search_results, top_k=top_k)
    context = "\n\n".join(f"[{index + 1}] {item['snippet']}" for index, item in enumerate(reranked))
    return context, reranked


def _build_prompt(context: str, query: str) -> str:
    return f"""Ответь на вопрос пользователя, используя только предоставленный контекст. Если ответа нет в контексте, скажи об этом.

Контекст:
{context}

Вопрос: {query}

Ответ:"""


async def ask_query(query: str, top_k: int = None, filters: Optional[dict] = None) -> Dict[str, Any]:
    try:
        context, sources = await _build_rag_context(query, top_k=top_k)
        prompt = _build_prompt(context, query)
        answer = _current_provider().complete(prompt)
        _record_provider_success()
        return {
            "answer": answer,
            "sources": [
                {
                    "path": item["path"],
                    "filename": item["filename"],
                    "snippet": item["snippet"],
                    "score": item["score"],
                    "rerank_score": item.get("rerank_score"),
                }
                for item in sources
            ],
        }
    except Exception as e:
        _record_provider_failure()
        raise


async def ask_query_stream(
    query: str,
    top_k: int = None,
    filters: Optional[dict] = None,
) -> AsyncGenerator[str, None]:
    """SSE-стриминг ответа LLM. Первым идёт JSON с источниками, затем токены ответа."""
    try:
        context, sources = await _build_rag_context(query, top_k=top_k)
        prompt = _build_prompt(context, query)

        sources_payload = {
            "type": "sources",
            "sources": [
                {
                    "path": item["path"],
                    "filename": item["filename"],
                    "snippet": item["snippet"],
                    "score": item["score"],
                    "rerank_score": item.get("rerank_score"),
                }
                for item in sources
            ],
        }
        yield f"data: {json.dumps(sources_payload, ensure_ascii=False)}\n\n"

        token_count = 0
        for token in _current_provider().stream_complete(prompt):
            token_count += 1
            payload = {"type": "token", "content": token}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        # Успешный стриминг завершён
        _record_provider_success()
        yield "data: [DONE]\n\n"

    except Exception as exc:
        _record_provider_failure()
        error_payload = {"type": "error", "message": str(exc)}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        error_payload = {"type": "error", "message": str(exc)}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
