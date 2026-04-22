#!/usr/bin/env python3
"""
Smoke tests для FleshRAG API.
Проверяет базовую работоспособность всех основных эндпоинтов.
"""

import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ Установите requests: pip install requests")
    sys.exit(1)

BASE_URL = "http://localhost:8000"
OLLAMA_URL = "http://localhost:11434"
QDRANT_URL = "http://localhost:6333"

passed = 0
failed = 0
errors = []


def log(msg: str, level: str = "info"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    prefix = "✅" if level == "ok" else "❌" if level == "fail" else "  "
    print(f"{prefix} [{timestamp}] {msg}")


def test_endpoint(name: str, method: str, url: str, expected_status: int = 200, **kwargs):
    global passed, failed
    try:
        resp = getattr(requests, method)(url, timeout=30, **kwargs)
        if resp.status_code == expected_status:
            log(f"{name}: {resp.status_code}", "ok")
            passed += 1
            return resp
        else:
            log(f"{name}: ожидался {expected_status}, получен {resp.status_code}", "fail")
            errors.append(f"{name}: статус {resp.status_code}")
            failed += 1
            return None
    except requests.exceptions.RequestException as e:
        log(f"{name}: {e}", "fail")
        errors.append(f"{name}: {e}")
        failed += 1
        return None


def print_header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


# ============================================
# Health checks
# ============================================
print_header("1. Health Checks")

test_endpoint("Backend health", "get", f"{BASE_URL}/api/health")
test_endpoint("Ollama API", "get", f"{OLLAMA_URL}/api/tags")
test_endpoint("Qdrant API", "get", f"{QDRANT_URL}/")  # Health endpoint

# ============================================
# Index status
# ============================================
print_header("2. Index Status")

resp = test_endpoint("Index status", "get", f"{BASE_URL}/api/index/status")
if resp:
    data = resp.json()
    stats = data.get("stats", {})
    indexed = stats.get("indexed", 0)
    total = stats.get("total", 0)
    log(f"Индексировано файлов: {indexed}/{total}")
    if indexed == 0:
        errors.append("Нет проиндексированных файлов")

# ============================================
# Search API
# ============================================
print_header("3. Search API")

test_endpoint(
    "Search query",
    "post",
    f"{BASE_URL}/api/search",
    json={"query": "тест", "top_k": 5}
)

# ============================================
# RAG API (Ask)
# ============================================
print_header("4. RAG API (Ask)")

test_endpoint(
    "Ask question",
    "post",
    f"{BASE_URL}/api/ask",
    json={"query": "Что такое FleshRAG?", "top_k": 3}
)

# ============================================
# Conversations API
# ============================================
print_header("5. Conversations API")

# Создать диалог
resp = test_endpoint(
    "Create conversation",
    "post",
    f"{BASE_URL}/api/conversations",
    json={"title": "Smoke Test Dialog"}
)

conv_id = None
if resp:
    conv_id = resp.json().get("id")
    log(f"Создан диалог #{conv_id}")

# Список диалогов
test_endpoint("List conversations", "get", f"{BASE_URL}/api/conversations")

# Вопрос в диалоге
if conv_id:
    test_endpoint(
        f"Ask in conversation #{conv_id}",
        "post",
        f"{BASE_URL}/api/conversations/{conv_id}/ask",
        json={"query": "Какие файлы проиндексированы?"}
    )

# ============================================
# Files API
# ============================================
print_header("6. Files API")

test_endpoint("List files", "get", f"{BASE_URL}/api/files")
test_endpoint("File types", "get", f"{BASE_URL}/api/files/types")

# ============================================
# Export API
# ============================================
print_header("7. Export API")

if conv_id:
    test_endpoint(
        "Export conversation",
        "get",
        f"{BASE_URL}/api/export/conversation/{conv_id}"
    )

test_endpoint(
    "Export search results",
    "post",
    f"{BASE_URL}/api/export/search",
    params={"query": "test"},
    json=[{"filename": "test.txt", "path": "/test", "snippet": "test", "score": 0.5}]
)

# ============================================
# Settings API
# ============================================
print_header("8. Settings API")

test_endpoint("Get settings", "get", f"{BASE_URL}/api/settings")

# ============================================
# Admin API
# ============================================
print_header("9. Admin API")

test_endpoint("Admin status", "get", f"{BASE_URL}/api/admin/status")
test_endpoint("Admin settings", "get", f"{BASE_URL}/api/admin/settings")
test_endpoint("Admin budget", "get", f"{BASE_URL}/api/admin/budget/stats")

# ============================================
# Models API
# ============================================
print_header("10. Models API")

test_endpoint("List models", "get", f"{BASE_URL}/api/models")

# ============================================
# Summary
# ============================================
print_header("Smoke Tests Summary")

total = passed + failed
print(f"\n  Всего тестов:  {total}")
print(f"  ✅ Прошло:     {passed}")
print(f"  ❌ Провалено:  {failed}")

if errors:
    print(f"\n  Ошибки:")
    for err in errors:
        print(f"    - {err}")

print(f"\n{'='*60}\n")

# Exit code
sys.exit(0 if failed == 0 else 1)
