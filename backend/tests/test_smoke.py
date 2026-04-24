"""Smoke tests for basic API health and connectivity."""

import pytest
import httpx


BASE_URL = "http://localhost:8000"


@pytest.mark.smoke
def test_health_check():
    """Test basic health endpoint."""
    response = httpx.get(f"{BASE_URL}/api/health", timeout=10.0)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert "components" in data
    assert "database" in data["components"]
    assert "qdrant" in data["components"]


@pytest.mark.smoke
def test_ready_endpoint():
    """Test readiness endpoint contract."""
    response = httpx.get(f"{BASE_URL}/api/ready", timeout=10.0)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["ready", "degraded"]
    assert "database" in data
    assert "qdrant" in data
    assert "provider" in data


@pytest.mark.smoke
def test_api_root():
    """Test API root endpoint (may return 404 if not implemented)."""
    response = httpx.get(f"{BASE_URL}/", timeout=10.0)
    # Root may return 404 (not implemented) or 200
    assert response.status_code in [200, 404]


@pytest.mark.smoke
def test_search_endpoint_exists():
    """Test that search endpoint exists."""
    # Try POST method as search typically uses POST
    # Note: May return 500 if no collection exists - that's OK for smoke test
    response = httpx.post(f"{BASE_URL}/api/search", json={"query": "test"}, timeout=10.0)
    # Should return 200 (success), 422 (validation error), 500 (no collection) - not 404
    assert response.status_code in [200, 422, 405, 500]  # 500 if collection doesn't exist yet


@pytest.mark.smoke
def test_ask_endpoint_exists():
    """Test that ask endpoint exists (returns 422 for missing query, not 404)."""
    response = httpx.post(f"{BASE_URL}/api/ask", json={}, timeout=10.0)
    # Should return 422 (validation error) or 200, not 404
    assert response.status_code in [200, 422]


@pytest.mark.smoke
def test_files_endpoint_exists():
    """Test that files endpoint exists."""
    response = httpx.get(f"{BASE_URL}/api/files", timeout=10.0)
    assert response.status_code in [200, 401, 403]  # May require auth


@pytest.mark.smoke
def test_index_status_endpoint():
    """Test index status endpoint."""
    response = httpx.get(f"{BASE_URL}/api/index/status", timeout=10.0)
    assert response.status_code in [200, 401, 403]
