from typing import List, Optional, Dict, Any

from qdrant_client import QdrantClient
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings

from app.config import settings
from app.indexer.embedder import COLLECTION_NAME

qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)

embedder = OllamaEmbedding(model_name=settings.embed_model, base_url=settings.ollama_host)
llm = Ollama(model=settings.llm_model, base_url=settings.ollama_host, request_timeout=120.0)

Settings.embed_model = embedder
Settings.llm = llm


async def search_query(query: str, top_k: int = 10, filters: Optional[dict] = None) -> List[Dict[str, Any]]:
    embedding = embedder.get_text_embedding(query)
    search_result = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=embedding,
        limit=top_k,
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
        })
    return results


async def ask_query(query: str, top_k: int = 5, filters: Optional[dict] = None) -> Dict[str, Any]:
    results = await search_query(query, top_k=top_k, filters=filters)
    context = "\n\n".join([f"[{i+1}] {r['snippet']}" for i, r in enumerate(results)])
    prompt = f"""Ответь на вопрос пользователя, используя только предоставленный контекст. Если ответа нет в контексте, скажи об этом.

Контекст:
{context}

Вопрос: {query}

Ответ:"""
    response = llm.complete(prompt)
    return {
        "answer": response.text,
        "sources": [{"path": r["path"], "filename": r["filename"], "snippet": r["snippet"], "score": r["score"]} for r in results],
    }
