# Техническое задание: Multimodal RAG — семантический поиск по файлам на домашнем PC

**Версия:** 2.1 (добавлены: ffmpeg-пайплайн аудио/видео, local reranker с full реализацией)  
**Дата:** апрель 2026

---

## 1. Цели и ограничения

### Цели
- Индексировать все типы файлов на указанных дисках/директориях
- Отвечать на вопросы на естественном языке по содержимому файлов (RAG)
- Показывать источники с превью и ссылками на оригиналы
- Работать полностью офлайн (local-режим) или с облачными моделями (cloud-режим)
- Облачные модели — **режим по умолчанию** при наличии API-ключа

### Целевой профиль железа
- CPU: 4–8 ядер (x86-64), без GPU или слабая GPU
- RAM: 8–16 GB
- ОС хоста: Windows 11 / WSL2 или Linux Ubuntu 22.04+
- Интернет: необязателен (система работает без него в local-режиме)

---

## 2. Технологический стек

### 2.1 Слой инференса: облако (по умолчанию)

Провайдер: **neuraldeep.ru** — OpenAI-совместимый API.  
`Base URL: https://api.neuraldeep.ru/v1`  
`API ключ: хранится в .env, переменная NEURALDEEP_API_KEY`

| Назначение            | Модель               | Особенности                                        |
|-----------------------|----------------------|----------------------------------------------------|
| LLM (основная)        | `gpt-oss-120b`       | 131k ctx, tool calling, reasoning, MXFP4 · 2×RTX 4090 |
| LLM (экономичная)     | `qwen3.6-35b-a3b`    | 200k ctx, MoE A3B, дешевле в 4×                   |
| Embeddings (основные) | `e5-large`           | 1024-dim, multilingual, 3 реплики, кешируется      |
| Embeddings (alt)      | `bge-m3`             | 1024-dim, 8k ctx                                   |
| Reranker              | `bge-reranker`       | Cross-encoder, встроенный `/v1/rerank`             |
| Транскрипция аудио    | `whisper-1`          | Multilingual, $0.003/мин                           |

**Тарифный план neuraldeep.ru (free tier L1):**
- Daily budget: $1.00 (~10M input-токенов на gpt-oss)
- RPM: 60 · Parallel: 4
- Streak-бонусы: +$0.10 за 3 дня подряд, +$0.20 за 7 дней, +$0.50 за 30 дней

**Ценообразование:**
- gpt-oss-120b / qwen3.6: $0.05 input · $0.20 output за 1M токенов
- e5-large / bge-m3: $0.03 input за 1M токенов
- whisper-1: $0.003 за минуту аудио

**Оптимизация расходов:**
- Использовать `user: <session_id>` для sticky-сессий (prefix cache warm, до 10× экономия)
- Для эмбеддингов — batching по 64 строки, результаты кешируются на стороне neuraldeep
- Для длинных документов — `qwen3.6-35b-a3b` дешевле при том же качестве
- Логировать расход токенов в SQLite для мониторинга бюджета

### 2.2 Слой инференса: локальный (fallback / offline)

Провайдер: **Ollama** — запускается в Docker-контейнере на хосте.

| Назначение          | Модель                    | Размер GGUF Q4 | Условие использования               |
|---------------------|---------------------------|----------------|--------------------------------------|
| LLM                 | `qwen2.5:3b`              | ~2.0 GB        | Offline / лимит бюджета              |
| LLM (fallback)      | `phi4-mini:3.8b`          | ~2.3 GB        | Альтернатива                         |
| Текст. эмбеддинги   | `nomic-embed-text`        | ~270 MB        | Offline embeddings                   |
| Транскрипция        | `faster-whisper` (base)   | ~145 MB        | Offline audio — base значительно лучше tiny на русском, CPU INT8 |

### 2.3 Model Router / Adapter

Центральный компонент, абстрагирующий вызовы моделей.  
Оба провайдера реализуют OpenAI-совместимый API — роутер переключает `base_url` и `api_key`.

```python
# app/models/router.py
class ModelRouter:
    providers = {
        "cloud": {
            "base_url": "https://api.neuraldeep.ru/v1",
            "api_key": settings.NEURALDEEP_API_KEY,
            "llm": "gpt-oss-120b",
            "embed": "e5-large",
            "rerank": "bge-reranker",
            "whisper": "whisper-1",
        },
        "local": {
            "base_url": "http://ollama:11434/v1",
            "api_key": "ollama",
            "llm": "qwen2.5:3b",
            "embed": "nomic-embed-text",
            "rerank": "cross-encoder/ms-marco-MiniLM-L-6-v2",  # HuggingFace, ~85 MB
            "whisper": None,          # faster-whisper запускается отдельным Python-процессом
        }
    }

    def get_client(self, provider: str = None) -> OpenAI:
        p = provider or settings.ACTIVE_PROVIDER  # берётся из БД/настроек
        cfg = self.providers[p]
        return OpenAI(api_key=cfg["api_key"], base_url=cfg["base_url"])
```

**Логика переключения:**
- `ACTIVE_PROVIDER=cloud` — по умолчанию, если задан `NEURALDEEP_API_KEY`
- `ACTIVE_PROVIDER=local` — если ключ не задан или выбрано вручную из Admin Console
- **Auto-fallback:** при HTTP 429 / 503 от neuraldeep автоматически переключается на local и пишет событие в лог
- **Модель в запросе:** можно переопределить конкретную модель на уровне запроса (для тестирования)

**Rerank в local-режиме:**  
В cloud доступен `bge-reranker` через `/v1/rerank`. В local-режиме используется `cross-encoder/ms-marco-MiniLM-L-6-v2` из HuggingFace (~85 MB), загружается один раз при старте worker-контейнера и остаётся в памяти. Полное описание реализации — в разделе 2.8.

### 2.4 Backend (Python)

| Компонент           | Технология                    | Зачем                                    |
|---------------------|-------------------------------|------------------------------------------|
| API-сервер          | **FastAPI** + uvicorn         | Async REST + SSE для стриминга           |
| RAG-оркестрация     | **LlamaIndex** 0.12+          | Query engine, retrieval pipeline         |
| Задачи индексации   | **Celery** + Redis            | Фоновая очередь индексации               |
| Мониторинг файлов   | **Watchdog**                  | Инкрементальная индексация               |
| ORM / метаданные    | **SQLAlchemy** + **SQLite**   | Метаданные файлов, настройки, токен-лог  |

### 2.5 Парсеры и медиа-препроцессинг

| Тип файла        | Библиотека / инструмент                 | Примечание                              |
|------------------|-----------------------------------------|-----------------------------------------|
| PDF              | `pymupdf` (fitz)                        | Текст, таблицы, встроенные изображения  |
| DOCX/XLSX/PPTX   | `python-docx`, `openpyxl`, `python-pptx`| Нативный парсинг Office-форматов       |
| Изображения (OCR)| `easyocr`                               | Кириллица, детектор CRAFT               |
| Аудио            | `ffmpeg` → `faster-whisper`             | Ресемплинг → транскрипция               |
| Видео            | `ffmpeg` → `faster-whisper` + кадры     | Аудиодорожка + 1 fps → CLIP/EasyOCR    |
| Код              | `tree-sitter`                           | AST-чанкинг функций и классов           |
| Общий fallback   | `markitdown` (Microsoft)                | Любой файл → Markdown                  |

**ffmpeg** устанавливается в Docker-образ backend одной строкой и используется как системная утилита через `subprocess`:

```dockerfile
# backend/Dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
# ... остальные зависимости
```

**Пайплайн аудио/видео → текст:**

```
Видеофайл (MP4, MKV, AVI...)         Аудиофайл (MP3, WAV, OGG...)
         │                                        │
         ▼                                        ▼
ffmpeg: извлечь аудиодорожку          ffmpeg: ресемплинг (если нужно)
  -vn -ar 16000 -ac 1 -c:a pcm_s16le         -ar 16000 -ac 1
         │                                        │
         └──────────────┬─────────────────────────┘
                        ▼
             temp_{uuid}.wav  (16 kHz моно WAV)
                        │
                        ▼
              cloud: whisper-1 (neuraldeep.ru)
              local: faster-whisper base INT8
                        │
                        ▼
              текст + временны́е метки сегментов
                        │
                        ▼
              Chunker → эмбеддинг → Qdrant
                        │
              удалить temp-файл
```

Реализация препроцессинга:

```python
# app/indexer/parsers/audio.py
import subprocess, uuid, os
from pathlib import Path

TMP_DIR = Path("/tmp/rag_audio")
TMP_DIR.mkdir(exist_ok=True)

def to_wav(src_path: str) -> str:
    """Конвертирует любой аудио/видео файл в 16 kHz моно WAV."""
    out = TMP_DIR / f"{uuid.uuid4()}.wav"
    subprocess.run(
        [
            "ffmpeg", "-i", src_path,
            "-vn",               # без видеодорожки
            "-ar", "16000",      # 16 kHz — требование Whisper
            "-ac", "1",          # моно
            "-c:a", "pcm_s16le", # несжатый WAV
            str(out), "-y", "-loglevel", "error"
        ],
        check=True
    )
    return str(out)

def extract_frames(video_path: str, fps: int = 1) -> list[str]:
    """Извлекает кадры из видео для визуального анализа (CLIP/EasyOCR)."""
    out_dir = TMP_DIR / f"frames_{uuid.uuid4()}"
    out_dir.mkdir()
    subprocess.run(
        [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps={fps}",          # 1 кадр в секунду
            "-q:v", "3",                   # качество JPEG
            str(out_dir / "frame_%04d.jpg"),
            "-loglevel", "error"
        ],
        check=True
    )
    return sorted(str(p) for p in out_dir.glob("*.jpg"))
```

**Транскрипция (cloud/local через роутер):**

```python
# app/indexer/parsers/transcriber.py
from faster_whisper import WhisperModel
from app.models.router import ModelRouter

_local_model: WhisperModel | None = None

def get_local_model() -> WhisperModel:
    global _local_model
    if _local_model is None:
        # base INT8 — оптимум для CPU: качество >> tiny, RAM ~350 MB
        _local_model = WhisperModel("base", device="cpu", compute_type="int8")
    return _local_model

def transcribe(audio_path: str, router: ModelRouter) -> str:
    if router.active_provider == "cloud":
        with open(audio_path, "rb") as f:
            result = router.get_client().audio.transcriptions.create(
                model="whisper-1", file=f
            )
        return result.text
    else:
        model = get_local_model()
        segments, _ = model.transcribe(
            audio_path,
            language="ru",
            beam_size=3,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500}
        )
        return " ".join(s.text.strip() for s in segments)

def process_media_file(file_path: str, router: ModelRouter) -> str:
    """Полный пайплайн: любой медиафайл → текст."""
    from .audio import to_wav
    wav = to_wav(file_path)
    try:
        return transcribe(wav, router)
    finally:
        os.unlink(wav)  # удалить временный файл
```

### 2.6 Local Reranker

В local-режиме используется **`cross-encoder/ms-marco-MiniLM-L-6-v2`** из HuggingFace.

| Параметр     | Значение                                         |
|--------------|--------------------------------------------------|
| Размер       | ~85 MB                                           |
| Архитектура  | BERT-base cross-encoder                          |
| Скорость     | ~50 мс на батч из 20 пар (CPU)                   |
| Русский язык | удовлетворительно (обучен на MS MARCO, английский)|

Для лучшего качества на русском — альтернатива `DiTy/cross-encoder-russian-msmarco` (~110 MB), дообученная на русском MSMARCO. Выбор модели задаётся в Admin Console (dropdown в разделе «Модели»).

**Реализация:**

```python
# app/rag/reranker.py
from sentence_transformers import CrossEncoder
from app.core.config import settings

_model: CrossEncoder | None = None

def get_reranker() -> CrossEncoder:
    global _model
    if _model is None:
        # Загружается один раз при первом обращении, остаётся в памяти worker
        _model = CrossEncoder(settings.LOCAL_RERANKER_MODEL, max_length=512)
    return _model

def rerank_local(query: str, candidates: list[str], top_n: int = 5) -> list[int]:
    """Возвращает индексы candidates, отсортированные по релевантности."""
    model = get_reranker()
    pairs = [(query, doc) for doc in candidates]
    scores = model.predict(pairs)                         # numpy array
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return ranked[:top_n]
```

**Унифицированный интерфейс через ModelRouter:**

```python
# app/models/router.py  (метод rerank)
def rerank(self, query: str, candidates: list[str], top_n: int = 5) -> list[int]:
    if self.active_provider == "cloud":
        # bge-reranker через neuraldeep.ru /v1/rerank
        resp = self._raw_post("/rerank", {
            "model": "bge-reranker",
            "query": query,
            "documents": candidates
        })
        # API возвращает уже отсортированный список
        return [r["index"] for r in resp["results"]][:top_n]
    else:
        from app.rag.reranker import rerank_local
        return rerank_local(query, candidates, top_n)
```

**Настройка в `.env` / Admin Console:**
```env
LOCAL_RERANKER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
# Или для лучшего русского:
# LOCAL_RERANKER_MODEL=DiTy/cross-encoder-russian-msmarco
```

**Добавить в `pyproject.toml`:**
```toml
[tool.poetry.dependencies]
sentence-transformers = "^3.0"   # включает CrossEncoder + SentenceTransformer
```

`sentence-transformers` уже используется для local embeddings (`multilingual-e5-large`) — зависимость не добавляет новый пакет.

---

### 2.7 Векторная БД

**Qdrant** (self-hosted Docker):
- `on_disk: true` — векторы на SSD, не в RAM
- Scalar Quantization INT8 — экономия RAM в 4×
- Коллекции: `text_index` (768-dim для nomic / 1024-dim для e5-large)  
  Размерность зависит от активного провайдера — создаётся при инициализации
- При смене провайдера embeddings — требуется переиндексация (предупреждение в Admin Console)

### 2.8 Frontend

**Search UI:** React 18 + Vite + Tailwind CSS v4 + shadcn/ui  
**Admin Console:** отдельный React SPA, проксируется через nginx на `/admin`

---

## 3. Архитектура системы

```
┌──────────────────────────────────────────────────────────────────┐
│  Источники: документы / изображения / аудио / код                │
└──────────────────────────┬───────────────────────────────────────┘
                           │ Watchdog (inotify)
                    Celery Queue (Redis)
                           │
              ┌────────────▼────────────┐
              │  Parser / Chunker       │
              │  PyMuPDF · EasyOCR      │
              │  faster-whisper · AST   │
              └────────────┬────────────┘
                           │
              ┌────────────▼────────────────────────────┐
              │         Model Router / Adapter           │
              │  ACTIVE_PROVIDER: cloud | local          │
              └─────────┬──────────────────┬────────────┘
                        │ default          │ fallback / offline
          ┌─────────────▼──────┐  ┌────────▼──────────────────┐
          │  neuraldeep.ru     │  │  Ollama (local)           │
          │  e5-large (embed)  │  │  nomic-embed-text         │
          │  bge-reranker      │  │  cross-encoder (HF)       │
          │  gpt-oss-120b      │  │  qwen2.5:3b               │
          └─────────┬──────────┘  └────────┬──────────────────┘
                    └──────────┬───────────┘
                               │
                   ┌───────────▼──────────┐
                   │  Qdrant + SQLite      │
                   └───────────┬──────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
  ┌─────▼──────┐    ┌──────────▼──────────┐  ┌───────▼──────────┐
  │ Search UI  │    │  FastAPI / LlamaIndex│  │  Admin Console   │
  │ React+Vite │◄──►│  REST + SSE stream  │◄►│  React SPA       │
  └────────────┘    └─────────────────────┘  └──────────────────┘
```

---

## 4. Admin Console

### 4.1 Назначение

Веб-панель для управления системой без перезапуска Docker вручную.  
Доступна по адресу `http://localhost:3000/admin`.  
Базовая HTTP-аутентификация (логин/пароль в `.env`).

### 4.2 Разделы интерфейса

#### Раздел «Модели»
- **Переключатель провайдера:** `☁ Cloud (neuraldeep.ru)` / `⚙ Local (Ollama)` — радиокнопка, применяется мгновенно без рестарта
- **Выбор конкретных моделей:**
  - LLM модель (dropdown): для cloud — `gpt-oss-120b` / `qwen3.6-35b-a3b`; для local — все модели, доступные в Ollama
  - Embedding модель (dropdown): `e5-large` / `bge-m3` для cloud; `nomic-embed-text` / `multilingual-e5-large` для local
  - Reranker модель (dropdown): `bge-reranker` для cloud; `ms-marco-MiniLM-L-6-v2` / `DiTy/cross-encoder-russian-msmarco` для local
  - Предупреждение при смене embed-модели: _«Смена embedding-модели требует полной переиндексации. Продолжить?»_
- **Параметры LLM:** temperature, max_tokens, system prompt (редактируемое поле)
- **Тест подключения:** кнопка «Проверить» → ping к API, отображение latency и статуса

#### Раздел «Индексация»
- Прогресс-бар активной задачи (Celery task progress через WebSocket)
- Таблица статусов директорий: путь / файлов / проиндексировано / ошибок / последнее обновление
- Действия: «Переиндексировать всё», «Переиндексировать директорию», «Очистить индекс»
- Добавить/удалить директорию для наблюдения
- Исключения: паттерны glob (`.git/**`, `node_modules/**`, и др.)
- Фильтр расширений файлов

#### Раздел «Сервисы»
Таблица всех Docker-сервисов с состоянием и кнопками управления:

| Сервис    | Статус   | CPU  | RAM  | Действия            |
|-----------|----------|------|------|---------------------|
| backend   | ● running| 12%  | 280M | Restart · Logs      |
| worker    | ● running| 45%  | 512M | Restart · Logs      |
| ollama    | ● running| 5%   | 1.8G | Restart · Logs      |
| qdrant    | ● running| 2%   | 320M | Restart · Logs      |
| redis     | ● running| 0%   | 12M  | Restart · Logs      |
| frontend  | ● running| 0%   | 24M  | Restart · Logs      |

- **Restart** — перезапускает контейнер через Docker API (`docker restart <name>`)
- **Logs** — модальное окно с tail -200 логов контейнера (WebSocket live tail)
- **Restart All** — перезапускает все сервисы в правильном порядке

#### Раздел «Бюджет / Мониторинг»
- График расхода токенов за последние 7 дней (Chart.js, данные из SQLite token_log)
- Текущий дневной расход vs лимит ($1.00): прогресс-бар с цветовой индикацией
- Таблица: запросы по типу (embeddings / completions / rerank / audio)
- Предупреждение при достижении 80% дневного лимита (уведомление в UI)
- Кнопка «Переключить в local» — быстрый переход при исчерпании бюджета

#### Раздел «Логи»
- Объединённый лог всех сервисов с фильтром по уровню (INFO / WARN / ERROR)
- Поиск по тексту в логах
- Экспорт в .txt

### 4.3 Backend API для Admin Console

```
GET  /api/admin/status              — статус всех сервисов (Docker stats)
GET  /api/admin/settings            — текущие настройки (провайдер, модели, директории)
PUT  /api/admin/settings            — обновить настройки (провайдер, модель, параметры)
POST /api/admin/services/{name}/restart  — перезапустить Docker-контейнер
GET  /api/admin/services/{name}/logs     — tail логов (SSE stream)
POST /api/admin/index/trigger       — запустить индексацию
POST /api/admin/index/reindex-all   — полная переиндексация
GET  /api/admin/budget/stats        — статистика расхода токенов
POST /api/admin/models/test         — проверить подключение к провайдеру
GET  /api/admin/ollama/models       — список доступных моделей в Ollama
POST /api/admin/ollama/pull         — скачать модель в Ollama
```

**Docker API в backend:**
Для управления контейнерами бэкенд использует `docker` Python SDK:
```python
import docker
client = docker.from_env()

def restart_service(name: str):
    container = client.containers.get(f"rag_{name}_1")
    container.restart()

def tail_logs(name: str, lines: int = 200):
    container = client.containers.get(f"rag_{name}_1")
    return container.logs(stream=True, tail=lines)
```
Docker socket монтируется в backend-контейнер: `/var/run/docker.sock:/var/run/docker.sock:ro`.

### 4.4 Хранение настроек

Настройки Admin Console хранятся в SQLite (таблица `system_settings`), не в `.env`.  
`.env` содержит только секреты (API-ключи) и стартовые дефолты.  
При изменении провайдера через UI — запись в БД, `ModelRouter` читает актуальное значение при каждом запросе.

```sql
CREATE TABLE system_settings (
    key   TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- Примеры строк:
-- active_provider    | cloud
-- llm_model          | gpt-oss-120b
-- embed_model        | e5-large
-- llm_temperature    | 0.3
-- llm_max_tokens     | 1000
-- chunk_size         | 512
-- chunk_overlap      | 64
```

---

## 5. Структура проекта (обновлённая)

```
multimodal-rag/
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── search.py
│   │   │   ├── ask.py
│   │   │   ├── files.py
│   │   │   └── admin.py             # ← Admin API endpoints
│   │   ├── models/
│   │   │   ├── router.py            # ← Model Router / Adapter
│   │   │   ├── providers/
│   │   │   │   ├── cloud.py         # neuraldeep.ru client
│   │   │   │   └── local.py         # Ollama client
│   │   │   └── budget.py            # Логирование токенов, проверка лимитов
│   │   ├── indexer/
│   │   │   ├── watcher.py
│   │   │   ├── parsers/
│   │   │   └── chunker.py
│   │   ├── rag/
│   │   │   ├── pipeline.py
│   │   │   ├── reranker.py          # cloud bge-reranker или local cross-encoder
│   │   │   └── prompts.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   └── crud.py
│   │   └── tasks/
│   │       └── celery_app.py
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Search.tsx
│   │   │   └── admin/               # ← Admin Console SPA
│   │   │       ├── AdminLayout.tsx
│   │   │       ├── ModelsPage.tsx
│   │   │       ├── IndexingPage.tsx
│   │   │       ├── ServicesPage.tsx
│   │   │       ├── BudgetPage.tsx
│   │   │       └── LogsPage.tsx
│   │   └── components/
│   └── nginx.conf                   # /admin → React SPA, /api → backend
│
└── volumes/
    ├── qdrant_data/
    ├── sqlite_data/
    ├── ollama_models/
    └── redis_data/
```

---

## 6. Docker Compose (обновлённый)

```yaml
version: "3.9"

services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ./volumes/ollama_models:/root/.ollama
    ports:
      - "11434:11434"
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - ./volumes/qdrant_data:/qdrant/storage
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - ./volumes/redis_data:/data
    restart: unless-stopped

  backend:
    build: ./backend
    volumes:
      - ./volumes/sqlite_data:/app/data
      - /var/run/docker.sock:/var/run/docker.sock:ro  # для Admin restart
      - ${INDEX_PATHS}:/mnt/indexed:ro
    environment:
      NEURALDEEP_API_KEY: ${NEURALDEEP_API_KEY}
      NEURALDEEP_BASE_URL: https://api.neuraldeep.ru/v1
      OLLAMA_HOST: http://ollama:11434
      QDRANT_HOST: qdrant
      REDIS_URL: redis://redis:6379/0
      DATABASE_URL: sqlite:////app/data/metadata.db
      ADMIN_USERNAME: ${ADMIN_USERNAME:-admin}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD:-changeme}
      # Стартовый провайдер — переопределяется через Admin Console
      DEFAULT_PROVIDER: ${DEFAULT_PROVIDER:-cloud}
    ports:
      - "8000:8000"
    depends_on:
      - ollama
      - qdrant
      - redis
    restart: unless-stopped

  worker:
    build: ./backend
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2
    volumes:
      - ./volumes/sqlite_data:/app/data
      - ${INDEX_PATHS}:/mnt/indexed:ro
    environment:
      NEURALDEEP_API_KEY: ${NEURALDEEP_API_KEY}
      NEURALDEEP_BASE_URL: https://api.neuraldeep.ru/v1
      OLLAMA_HOST: http://ollama:11434
      QDRANT_HOST: qdrant
      REDIS_URL: redis://redis:6379/0
      DATABASE_URL: sqlite:////app/data/metadata.db
    depends_on:
      - redis
      - qdrant
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped
```

Файл `.env`:
```env
# Секреты
NEURALDEEP_API_KEY=sk-NSlYhFlLl6A_SEqLzkomTQ
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password

# Директории для индексации (разделитель :)
INDEX_PATHS=/c/Users/alex/Documents:/d/Projects:/d/Photos

# Стартовый провайдер (cloud | local)
DEFAULT_PROVIDER=cloud
```

---

## 7. Пример вызовов neuraldeep.ru из кода

### Chat completions (стриминг)
```python
from openai import OpenAI
from app.models.router import ModelRouter

router = ModelRouter()
client = router.get_client()  # вернёт cloud или local в зависимости от настроек

stream = client.chat.completions.create(
    model=router.current_llm,
    messages=[
        {"role": "system", "content": prompts.RAG_SYSTEM},
        {"role": "user", "content": query_with_context}
    ],
    max_tokens=1000,
    temperature=0.3,
    stream=True,
    user=session_id,  # sticky session для prefix cache
)
for chunk in stream:
    yield chunk.choices[0].delta.content or ""
```

### Embeddings (батч)
```python
response = client.embeddings.create(
    model=router.current_embed,   # e5-large (cloud) или nomic-embed-text (local)
    input=chunks_batch,           # список строк, батч до 64
)
vectors = [item.embedding for item in response.data]
```

### Rerank (единый интерфейс cloud/local)
```python
# Один вызов — роутер сам выбирает bge-reranker (cloud) или cross-encoder (local)
top_indices = router.rerank(query=query, candidates=[c.text for c in candidates], top_n=5)
reranked = [candidates[i] for i in top_indices]
```

### Транскрипция аудио/видео (с ffmpeg препроцессингом)
```python
from app.indexer.parsers.transcriber import process_media_file

# Работает для любого медиафайла: MP3, WAV, MP4, MKV, OGG и т.д.
# Внутри: ffmpeg ресемплирует → WAV 16kHz → cloud whisper-1 или local faster-whisper base
text = process_media_file(file_path, router)
```

Детали ffmpeg-пайплайна описаны в разделе 2.5.

---

## 8. Мониторинг бюджета

При каждом обращении к neuraldeep.ru — запись в SQLite:

```sql
CREATE TABLE token_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          DATETIME DEFAULT CURRENT_TIMESTAMP,
    provider    TEXT,          -- cloud | local
    model       TEXT,
    op_type     TEXT,          -- embed | completion | rerank | audio
    input_tok   INTEGER,
    output_tok  INTEGER,
    cost_usd    REAL,
    session_id  TEXT
);
```

Логика предупреждений:
- При достижении 80% дневного лимита — уведомление в Admin Console и поисковом UI
- При достижении 100% — автоматическое переключение на `local`, запись события в лог
- Admin Console: график расхода по дням + прогресс-бар текущего дня

---

## 9. Nginx конфигурация (frontend/nginx.conf)

```nginx
server {
    listen 80;

    # Search UI (основной)
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # Admin Console SPA
    location /admin {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /admin/index.html;
    }

    # API proxy
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        # SSE streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

---

## 10. Фазы разработки

### Фаза 1 — Ядро + облачные модели (2 недели)
- Docker Compose с Qdrant + Ollama + Redis
- Model Router с поддержкой neuraldeep.ru и Ollama (cloud по умолчанию)
- Парсеры: PDF, TXT, MD, DOCX
- FastAPI: `/search` и `/ask` с SSE-стримингом
- Простой Search UI: строка поиска + результаты

### Фаза 2 — Admin Console (1.5 недели)
- Раздел «Модели»: переключение провайдера, выбор LLM/embed
- Раздел «Сервисы»: статусы Docker, restart, live logs
- Раздел «Индексация»: статус, добавление директорий
- Базовая HTTP-аутентификация

### Фаза 3 — Мультимодальность (2 недели)
- Аудио: whisper-1 (cloud) / faster-whisper tiny (local)
- Изображения: EasyOCR + CLIP
- Видео: аудиодорожка + ключевые кадры
- Watchdog: инкрементальная индексация

### Фаза 4 — Мониторинг и качество (1 неделя)
- Раздел «Бюджет»: граф расхода, авто-переключение при лимите
- Cross-encoder rerank (bge-reranker cloud / HF local)
- Превью файлов в Search UI
- Фильтры поиска (тип, дата, директория)

---

## 11. Безопасность

- API-ключ neuraldeep.ru хранится только в `.env`, не попадает в репозиторий (`.gitignore`)
- Admin Console защищена Basic Auth (логин/пароль в `.env`)
- Docker socket монтируется только для backend — не для frontend
- Файлы монтируются read-only (`ro`)
- Все сервисы кроме frontend/backend недоступны снаружи Docker-сети

---

*Документ является стартовой точкой. Версии зафиксировать в `pyproject.toml` / `package.json` при инициализации проекта.*
