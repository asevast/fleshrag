"""Integration tests for external services connectivity."""

import pytest
import httpx
from qdrant_client import QdrantClient
import redis


BASE_URL = "http://localhost:8000"


@pytest.mark.integration
def test_qdrant_connectivity():
    """Test connection to Qdrant vector database."""
    client = QdrantClient(host="localhost", port=6333, timeout=10.0)
    # Should not raise an exception
    client.get_collections()


@pytest.mark.integration
def test_redis_connectivity():
    """Test connection to Redis."""
    r = redis.Redis(host="localhost", port=6379, socket_timeout=5.0)
    result = r.ping()
    assert result is True


@pytest.mark.integration
def test_ollama_connectivity():
    """Test connection to Ollama."""
    response = httpx.get("http://localhost:11434/api/tags", timeout=10.0)
    assert response.status_code == 200


@pytest.mark.integration
def test_embed_service_connectivity():
    """Test connection to embed-service."""
    response = httpx.get("http://localhost:8001/health", timeout=30.0)
    assert response.status_code == 200


@pytest.mark.integration
def test_rag_pipeline_health():
    """Test that RAG pipeline can be initialized (via health endpoint)."""
    response = httpx.get(f"{BASE_URL}/api/health", timeout=30.0)
    assert response.status_code == 200
    data = response.json()
    # Check that all components are healthy
    assert data["status"] == "healthy"
    assert "components" in data
    components = data["components"]
    assert "qdrant" in components
    assert "ollama" in components
    assert "redis" in components
