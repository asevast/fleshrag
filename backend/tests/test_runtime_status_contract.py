import sys
import types

from fastapi.testclient import TestClient

fake_markitdown = types.ModuleType("markitdown")
fake_markitdown.MarkItDown = object
sys.modules.setdefault("markitdown", fake_markitdown)

from app.main import app


def test_health_contract(monkeypatch):
    monkeypatch.setattr("app.main._component_snapshot", lambda: {
        "database": "ok",
        "qdrant": "ok",
        "redis": "ok",
        "ollama": "error",
        "provider": "local-fallback",
    })
    client = TestClient(app)

    response = client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["components"]["provider"] == "local-fallback"


def test_ready_contract(monkeypatch):
    monkeypatch.setattr("app.main._component_snapshot", lambda: {
        "database": "ok",
        "qdrant": "error",
        "redis": "ok",
        "ollama": "ok",
        "provider": "cloud-configured",
    })
    client = TestClient(app)

    response = client.get("/api/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "ok"
    assert data["qdrant"] == "error"
