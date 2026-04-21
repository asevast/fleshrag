import json
from datetime import datetime
from typing import List, Optional, Dict, Any, AsyncGenerator

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings

from app.config import settings
from app.indexer.embedder import COLLECTION_NAME
from app.rag.reranker import rerank

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

embedder = OllamaEmbedding(model_name=settings.embed_model, base_url=settings.ollama_host)
llm = Ollama(model=settings.llm_model, base_url=settings.ollama_host, request_timeout=120.0)

Settings.embed_model = embedder
Settings.llm = llm


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


async def search_query(query: str, top_k: int = None, filters: Optional[dict] = None) -> List[Dict[str, Any]]:
    top_k = top_k or settings.top_k_search
    embedding = embedder.get_text_embedding(query)
    
    qdrant_filter = _build_qdrant_filter(filters)
    
    search_result = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=top_k,
        query_filter=qdrant_filter,
        with_payload=True,
    )
    results = []
    for point in search_result:
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


async def _build_rag_context(query: str, top_k: int = None) -> tuple[str, List[Dict]]:
    """Выполняет поиск + reranking и возвращает контекст + источники."""
    top_k = top_k or settings.top_k_rerank
    search_results = await search_query(query, top_k=settings.top_k_search)
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
    response = llm.complete(prompt)
    return {
        "answer": response.text,
        "sources": [{"path": r["path"], "filename": r["filename"], "snippet": r["snippet"], "score": r["score"], "rerank_score": r.get("rerank_score")} for r in sources],
    }


async def ask_query_stream(query: str, top_k: int = None, filters: Optional[dict] = None) -> AsyncGenerator[str, None]:
    """SSE-стриминг ответа LLM. Первым идёт JSON с источниками, затем токены ответа."""
    try:
        context, sources = await _build_rag_context(query, top_k=top_k)
        prompt = _build_prompt(context, query)

        # Отправляем источники первым событием
        sources_payload = {
            "type": "sources",
            "sources": [{"path": r["path"], "filename": r["filename"], "snippet": r["snippet"], "score": r["score"], "rerank_score": r.get("rerank_score")} for r in sources],
        }
        yield f"data: {json.dumps(sources_payload, ensure_ascii=False)}\n\n"

        # Стриминг токенов от LLM
        stream_response = llm.stream_complete(prompt)
        for token in stream_response:
            payload = {"type": "token", "content": token.delta}
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

        yield "data: [DONE]\n\n"
    except Exception as e:
        error_payload = {"type": "error", "message": str(e)}
        yield f"data: {json.dumps(error_payload, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

