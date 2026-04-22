from __future__ import annotations

from typing import Iterator

from openai import OpenAI

from app.config import settings
from app.models.contracts import ProviderCapabilities


class CloudProvider:
    def __init__(
        self,
        *,
        llm_model: str,
        embed_model: str,
        rerank_model: str | None,
        temperature: float,
        max_tokens: int,
    ):
        self.client = OpenAI(
            api_key=settings.neuraldeep_api_key,
            base_url=settings.neuraldeep_base_url,
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.capabilities = ProviderCapabilities(
            provider="cloud",
            llm_model=llm_model,
            embed_model=embed_model,
            rerank_model=rerank_model,
            supports_rerank_api=bool(rerank_model),
        )

    def embed_text(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = self.client.embeddings.create(
            model=self.capabilities.embed_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        session_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str:
        response = self.client.chat.completions.create(
            model=self.capabilities.llm_model,
            messages=_build_messages(prompt, system_prompt),
            max_tokens=max_tokens or self.max_tokens,
            temperature=self.temperature if temperature is None else temperature,
            user=session_id,
        )
        return response.choices[0].message.content or ""

    def stream_complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        session_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[str]:
        stream = self.client.chat.completions.create(
            model=self.capabilities.llm_model,
            messages=_build_messages(prompt, system_prompt),
            max_tokens=max_tokens or self.max_tokens,
            temperature=self.temperature if temperature is None else temperature,
            user=session_id,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta

    def rerank(self, query: str, documents: list[str]) -> list[float] | None:
        if not self.capabilities.rerank_model or not documents:
            return None
        response = self.client.post(
            "/rerank",
            cast_to=dict,
            body={
                "model": self.capabilities.rerank_model,
                "query": query,
                "documents": documents,
            },
        )
        results = response.get("results", [])
        scores = [0.0] * len(documents)
        for item in results:
            index = item.get("index")
            if index is not None and 0 <= index < len(scores):
                scores[index] = float(item.get("relevance_score", 0.0))
        return scores

    def list_models(self) -> list[dict]:
        return [
            {"name": settings.cloud_llm_model, "provider": "cloud", "kind": "llm"},
            {"name": settings.cloud_llm_economy_model, "provider": "cloud", "kind": "llm"},
            {"name": settings.cloud_embed_model, "provider": "cloud", "kind": "embedding"},
            {"name": settings.cloud_embed_alt_model, "provider": "cloud", "kind": "embedding"},
        ]


def _build_messages(prompt: str, system_prompt: str | None) -> list[dict]:
    messages: list[dict] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    return messages

