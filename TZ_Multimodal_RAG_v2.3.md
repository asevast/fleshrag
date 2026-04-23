# Техническое задание: Multimodal RAG --- семантический поиск

**Версия:** 2.3 (интегрированные улучшения + код)\
**Дата:** 2026-04-23

------------------------------------------------------------------------

## 2.3 Model Router --- устойчивость (обновлено)

### Circuit Breaker

``` python
# app/models/circuit_breaker.py
import time

class CircuitBreaker:
    def __init__(self, fail_threshold=3, cooldown=60):
        self.fail_threshold = fail_threshold
        self.cooldown = cooldown
        self.fail_count = 0
        self.last_fail_time = 0
        self.open = False

    def record_success(self):
        self.fail_count = 0
        self.open = False

    def record_failure(self):
        self.fail_count += 1
        self.last_fail_time = time.time()
        if self.fail_count >= self.fail_threshold:
            self.open = True

    def can_execute(self):
        if not self.open:
            return True
        if time.time() - self.last_fail_time > self.cooldown:
            self.open = False
            self.fail_count = 0
            return True
        return False
```

Интеграция:

``` python
if provider == "cloud" and not breaker.can_execute():
    provider = "local"
```

------------------------------------------------------------------------

## 2.4 Индексация (обновлено)

### Fingerprint + идемпотентность

``` python
import hashlib
from pathlib import Path

def file_fingerprint(path: str) -> str:
    p = Path(path)
    stat = p.stat()
    base = f"{p.resolve()}_{stat.st_size}_{stat.st_mtime}"
    return hashlib.sha256(base.encode()).hexdigest()

def chunk_id(fp: str, idx: int) -> str:
    return hashlib.sha256(f"{fp}_{idx}".encode()).hexdigest()
```

------------------------------------------------------------------------

## 2.5 Cache слой

``` python
# app/cache/artifacts.py
import hashlib, json, os

CACHE_DIR = "/app/cache"

def cache_key(content: bytes, version: str):
    return hashlib.sha256(content + version.encode()).hexdigest()

def get_cached(key: str):
    path = f"{CACHE_DIR}/{key}.json"
    if os.path.exists(path):
        return json.load(open(path))
    return None

def set_cached(key: str, data):
    path = f"{CACHE_DIR}/{key}.json"
    json.dump(data, open(path, "w"))
```

------------------------------------------------------------------------

## 2.6 SQLite настройки

``` python
# при старте приложения
engine.execute("PRAGMA journal_mode=WAL;")
engine.execute("PRAGMA busy_timeout=5000;")
```

------------------------------------------------------------------------

## 2.7 GPU (CUDA auto-detect)

``` python
import torch

def get_device():
    return "cuda" if torch.cuda.is_available() else "cpu"
```

Использование:

``` python
device = get_device()
WhisperModel("base", device=device)
```

------------------------------------------------------------------------

## 2.8 Retry политики

``` python
import time

def retry(fn, retries=2, delay=1):
    for i in range(retries):
        try:
            return fn()
        except Exception:
            if i == retries - 1:
                raise
            time.sleep(delay)
```

------------------------------------------------------------------------

## 3. UX состояния (обновлено)

Система должна явно возвращать в API:

``` json
{
  "status": "ok | indexing | fallback | reindex_required",
  "provider": "cloud | local",
  "results": [...]
}
```

------------------------------------------------------------------------

## Итог

Добавлено: - circuit breaker - идемпотентная индексация - cache слой -
CUDA auto-detect - retry политики - явные статусы API

Все изменения локальные и не требуют переработки архитектуры.
