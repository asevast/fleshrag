from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator, Protocol


@dataclass
class ProviderCapabilities:
    provider: str
    llm_model: str
    embed_model: str
    rerank_model: str | None
    supports_rerank_api: bool


class InferenceProvider(Protocol):
    capabilities: ProviderCapabilities

    def embed_text(self, text: str) -> list[float]: ...

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        session_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> str: ...

    def stream_complete(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        session_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> Iterator[str]: ...

    def rerank(self, query: str, documents: list[str]) -> list[float] | None: ...

    def list_models(self) -> list[dict]: ...

