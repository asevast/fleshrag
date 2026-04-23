from __future__ import annotations

from typing import Iterator

import httpx
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama

from app.config import settings
from app.models.contracts import ProviderCapabilities


class LocalProvider:
    def __init__(
        self,
        *,
        llm_model: str,
        embed_model: str,
        rerank_model: str | None,
        temperature: float,
        max_tokens: int,
    ):
        self.embed_model = embed_model
        # Для multilingual-e5-large не используем OllamaEmbedding, он будет через embed-service
        if "multilingual-e5-large" not in embed_model:
            self.embedder = OllamaEmbedding(model_name=embed_model, base_url=settings.ollama_host)
        else:
            self.embedder = None
        self.llm = Ollama(model=llm_model, base_url=settings.ollama_host, request_timeout=120.0)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.capabilities = ProviderCapabilities(
            provider="local",
            llm_model=llm_model,
            embed_model=embed_model,
            rerank_model=rerank_model,
            supports_rerank_api=False,
        )

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        # multilingual-e5-large использует embed-service, остальные — Ollama
        if "multilingual-e5-large" in self.embed_model:
            return self._embed_via_service(texts)
        return self._embed_via_ollama(texts)
    
    def _embed_via_service(self, texts: list[str]) -> list[list[float]]:
        try:
            with httpx.Client() as client:
                response = client.post(
                    "http://embed_service:8001/embed",
                    json={"texts": texts, "is_query": False},
                    timeout=60.0,
                )
                response.raise_for_status()
                return response.json()["embeddings"]
        except httpx.HTTPError as e:
            raise RuntimeError(f"embed-service unavailable for multilingual-e5-large: {e}") from e
    
    def _embed_via_ollama(self, texts: list[str]) -> list[list[float]]:
        return self.embedder.get_text_embedding_batch(texts)

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        session_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        full_prompt = _build_prompt(prompt, system_prompt)
        response = self.llm.complete(full_prompt)
        return response.text

    def stream_complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        session_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[str]:
        full_prompt = _build_prompt(prompt, system_prompt)
        stream_response = self.llm.stream_complete(full_prompt)
        for token in stream_response:
            delta = getattr(token, "delta", "") or ""
            if delta:
                yield delta

    def rerank(self, query: str, documents: list[str]) -> list[float] | None:
        return None

    def list_models(self) -> list[dict]:
        with httpx.Client() as client:
            response = client.get(f"{settings.ollama_host}/api/tags", timeout=10.0)
            response.raise_for_status()
            data = response.json()
        return [
            {
                "name": model.get("name", ""),
                "size": model.get("size", 0),
                "digest": model.get("digest", ""),
                "modified_at": model.get("modified_at", ""),
                "provider": "local",
            }
            for model in data.get("models", [])
        ]


def _build_prompt(prompt: str, system_prompt: str | None) -> str:
    return f"{system_prompt}\n\n{prompt}" if system_prompt else prompt

