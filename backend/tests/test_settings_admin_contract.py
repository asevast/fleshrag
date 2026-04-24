import sys
import types

from fastapi.testclient import TestClient

fake_markitdown = types.ModuleType("markitdown")
fake_markitdown.MarkItDown = object
sys.modules.setdefault("markitdown", fake_markitdown)

from app.main import app


def test_settings_contract(monkeypatch):
    class DummyService:
        def __init__(self, db=None):
            pass

        def get_active_provider(self):
            return "local"

        def get_llm_model(self):
            return "qwen"

        def get_embed_model(self):
            return "e5"

        def get_rerank_model(self):
            return None

        def get_chunk_size(self):
            return 512

        def get_chunk_overlap(self):
            return 64

        def get_top_k_search(self):
            return 20

        def get_top_k_rerank(self):
            return 5

        def get_temperature(self):
            return 0.3

        def get_max_tokens(self):
            return 1000

    monkeypatch.setattr("app.api.settings.SettingsService", DummyService)

    client = TestClient(app)
    response = client.get("/api/settings")

    assert response.status_code == 200
    data = response.json()
    assert data["active_provider"] == "local"
    assert data["llm_model"] == "qwen"
    assert "llm_temperature" in data


def test_admin_router_is_registered(monkeypatch):
    monkeypatch.setattr("app.api.admin.ModelRouter.get_provider", lambda self: types.SimpleNamespace(
        capabilities=types.SimpleNamespace(
            provider="local",
            llm_model="qwen",
            embed_model="e5",
            rerank_model=None,
        )
    ))
    monkeypatch.setattr("app.api.admin.crud.get_index_stats", lambda db: {"pending": 0, "indexed": 1, "total": 1})

    client = TestClient(app)
    response = client.get("/api/admin/status")

    assert response.status_code == 200
    data = response.json()
    assert data["provider"] == "local"
    assert data["models"]["llm"] == "qwen"
