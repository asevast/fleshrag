import pytest

from app.config import Settings
from app.indexer import embedder
from app.rag import pipeline


def test_settings_fall_back_to_local_without_cloud_key():
    settings = Settings(default_provider="cloud", neuraldeep_api_key="")

    assert settings.llm_model == settings.local_llm_model
    assert settings.embed_model == settings.local_embed_model


@pytest.mark.asyncio
async def test_ask_query_uses_router_provider(monkeypatch):
    class DummyProvider:
        def complete(self, prompt: str) -> str:
            self.prompt = prompt
            return "router-answer"

    provider = DummyProvider()

    async def fake_context(query: str, top_k=None):
        return "context", [
            {"path": "/tmp/doc.txt", "filename": "doc.txt", "snippet": "snippet", "score": 0.9}
        ]

    monkeypatch.setattr(pipeline, "_build_rag_context", fake_context)
    monkeypatch.setattr(pipeline.router, "get_provider", lambda provider_name=None: provider)

    result = await pipeline.ask_query("question")

    assert result["answer"] == "router-answer"
    assert result["sources"][0]["filename"] == "doc.txt"
    assert "Контекст:" in provider.prompt


def test_embedder_uses_router_provider_batches(monkeypatch):
    class DummyProvider:
        def __init__(self):
            self.calls = []

        def embed_texts(self, texts: list[str]) -> list[list[float]]:
            self.calls.append(texts)
            return [[float(index + 1), float(index + 2)] for index, _ in enumerate(texts)]

    provider = DummyProvider()
    captured = {}

    monkeypatch.setattr(embedder.router, "get_provider", lambda provider_name=None: provider)
    monkeypatch.setattr(embedder.qdrant, "collection_exists", lambda name: True)
    monkeypatch.setattr(embedder.qdrant, "upsert", lambda collection_name, points: captured.update({"collection": collection_name, "points": points}))

    embedder.embed_and_upsert(["alpha", "beta"], "/tmp/file.txt", "file.txt", "text")

    assert provider.calls == [["alpha", "beta"]]
    assert captured["collection"] == embedder.COLLECTION_NAME
    assert len(captured["points"]) == 2
    assert captured["points"][0].payload["path"] == "/tmp/file.txt"
