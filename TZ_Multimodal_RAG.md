# Техническое задание: Multimodal RAG — семантический поиск по файлам на домашнем PC

**Версия:** 1.0  
**Дата:** апрель 2026  
**Назначение:** Локальная система на Docker для семантического поиска и ответов на вопросы по всем файлам на дисках (документы, изображения, аудио, код). Работает на слабом железе без GPU.

---

## 1. Цели и ограничения

### Цели
- Индексировать все типы файлов на указанных дисках/директориях
- Отвечать на вопросы на естественном языке по содержимому файлов
- Показывать источники с превью и ссылками на оригинальные файлы
- Работать полностью офлайн, без отправки данных во внешние сервисы

### Ограничения железа (целевой профиль)
- CPU: 4–8 ядер (x86-64), без дискретной GPU или слабая GPU (4–6 GB VRAM)
- RAM: 8–16 GB
- Диск: SSD предпочтителен, HDD допустим
- ОС хоста: Windows 11 / WSL2 или Linux Ubuntu 22.04+

### Ключевые принципы выбора стека
- Квантованные модели (GGUF Q4/Q5) через Ollama
- Небольшие embedding-модели (< 500 MB)
- Постепенная/инкрементальная индексация (не переиндексировать всё при каждом старте)
- Все сервисы в Docker Compose, без тяжёлых зависимостей на хосте

---

## 2. Технологический стек

### 2.1 Модели (запускаются через Ollama)

| Назначение         | Модель                        | Размер GGUF Q4 | Примечание                              |
|--------------------|-------------------------------|----------------|-----------------------------------------|
| LLM (генерация)    | `qwen2.5:3b`                  | ~2.0 GB        | Основная — быстрая, хороший русский     |
| LLM (fallback)     | `phi4-mini:3.8b`              | ~2.3 GB        | Альтернатива, сильнее в логике          |
| Текстовые эмбеддинги | `nomic-embed-text`          | ~270 MB        | 768-dim, SOTA для локального использования |
| Мультимодальные    | `llava-phi3:mini`             | ~2.5 GB        | Описание изображений (опционально)      |

> Всё скачивается через `ollama pull <model>` внутри Docker-контейнера при первом запуске.

### 2.2 Backend (Python)

| Компонент           | Технология                          | Зачем                                    |
|---------------------|-------------------------------------|------------------------------------------|
| API-сервер          | **FastAPI** + uvicorn               | Async REST + WebSocket для стриминга     |
| RAG-оркестрация     | **LlamaIndex** 0.12+                | Retrieval pipeline, query engine, rerank |
| Задачи индексации   | **Celery** + Redis                  | Фоновая очередь, не блокирует API        |
| Мониторинг файлов   | **Watchdog**                        | Инкрементальная индексация новых файлов  |
| Embedding-клиент    | `llama-index-embeddings-ollama`     | Интеграция с Ollama embeddings           |
| Reranker            | `cross-encoder/ms-marco-MiniLM-L-6` | Переранжирование top-N результатов       |
| ORM / метаданные    | **SQLAlchemy** + **SQLite**         | Хранение метаданных файлов, статус индекса |

### 2.3 Парсеры и экстракторы

| Тип файла     | Библиотека                              | Возможности                                  |
|---------------|-----------------------------------------|----------------------------------------------|
| PDF           | `pymupdf` (fitz)                        | Текст, таблицы, извлечение изображений из PDF |
| DOCX/XLSX/PPTX| `python-docx`, `openpyxl`, `python-pptx`| Нативный парсинг Office-форматов             |
| Изображения (OCR) | `easyocr`                           | Легче Tesseract, поддерживает кириллицу      |
| Аудио/видео   | `faster-whisper` (tiny/base)            | Транскрипция, ~CPU-only, малый footprint     |
| Код           | `tree-sitter`                           | AST-парсинг, умный чанкинг кода             |
| Общий fallback| `markitdown` (Microsoft)                | Конвертация любого файла → Markdown         |
| Архивы        | Встроенный `zipfile`/`tarfile`          | Распаковка и рекурсивная индексация          |

### 2.4 Векторная БД

**Qdrant** (self-hosted Docker) — оптимальный выбор для домашнего сервера:
- Хранит векторы на диске (не только в RAM), критично для слабых машин
- gRPC + REST API, встроенный payload-фильтр по метаданным
- Поддерживает квантование векторов (scalar quantization) — экономия памяти 4×
- Персистентное хранение в volume без внешнего хранилища

Настройки коллекции:
```
vector_size: 768       # nomic-embed-text
distance: Cosine
quantization: ScalarQuantization (INT8)
on_disk: true          # vectors хранятся на SSD, не в RAM
```

### 2.5 Frontend

| Компонент     | Технология                  | Зачем                              |
|---------------|-----------------------------|------------------------------------|
| UI-фреймворк  | **React 18** + **Vite**     | Быстрый HMR, лёгкая сборка         |
| Стилизация    | **Tailwind CSS** v4         | Утилитарные классы, без heavy CSS  |
| Компоненты    | **shadcn/ui**               | Unstyled radix-based компоненты    |
| Стриминг      | `EventSource` / WebSocket   | Потоковый вывод ответа LLM         |
| Превью файлов | `react-pdf`, `react-player` | Превью PDF и медиафайлов           |

### 2.6 Инфраструктура

| Сервис        | Docker-образ              | Назначение                        |
|---------------|---------------------------|-----------------------------------|
| `ollama`      | `ollama/ollama:latest`    | LLM + Embedding inference         |
| `qdrant`      | `qdrant/qdrant:latest`    | Векторная БД                      |
| `redis`       | `redis:7-alpine`          | Очередь задач Celery              |
| `backend`     | Custom Python 3.12        | FastAPI + Celery worker           |
| `frontend`    | Custom Node 20 (nginx)    | Статичный React-билд              |

---

## 3. Архитектура системы

### 3.1 Пайплайн индексации

```
Диск/директория
    │
    ├─ Watchdog (inotify/polling)
    │       │  Обнаружен новый/изменённый файл
    │       ▼
    ├─ Celery Queue (Redis)
    │       │  Задача на индексацию
    │       ▼
    ├─ Worker: Парсер/Экстрактор
    │   ├─ PDF → PyMuPDF → текст + изображения
    │   ├─ Аудио → faster-whisper → транскрипт
    │   ├─ Изображение → EasyOCR + CLIP-desc → текст
    │   └─ Код → tree-sitter → AST-чанки
    │       │
    │       ▼
    ├─ Chunker (LlamaIndex SentenceSplitter)
    │   chunk_size: 512 tokens, overlap: 64
    │       │
    │       ▼
    ├─ Embedder (nomic-embed-text via Ollama)
    │       │  768-мерный вектор на чанк
    │       ▼
    ├─ Qdrant (upsert с payload: path, filename, page, type, mtime)
    └─ SQLite (запись file_hash, indexed_at, chunk_count, status)
```

### 3.2 Пайплайн запроса

```
Пользователь → React UI → WebSocket → FastAPI
                                           │
                             1. Embed query (nomic-embed-text)
                                           │
                             2. Qdrant ANN-поиск (top-20)
                             + фильтрация по типу/дате (payload)
                                           │
                             3. Cross-encoder Reranker (top-5)
                                           │
                             4. LlamaIndex: собрать контекст
                                           │
                             5. Ollama LLM (qwen2.5:3b) → стриминг
                                           │
                                   WebSocket → UI (stream)
                                   + источники (path, page, preview)
```

### 3.3 Мультимодальная обработка

| Тип входных данных | Путь в системе                                                  |
|--------------------|-----------------------------------------------------------------|
| Текст в документе  | Прямая экстракция → эмбеддинг текста                           |
| Скан / фото        | EasyOCR → текст → эмбеддинг + CLIP image embedding             |
| Аудиозапись        | faster-whisper транскрипция → текстовый эмбеддинг              |
| Видеофайл          | Аудиодорожка → Whisper + кадры (1 fps) → CLIP или LLaVA-desc   |
| Исходный код       | tree-sitter AST → функции/классы как отдельные чанки            |
| Таблицы (XLSX/CSV) | openpyxl → Markdown-таблица → эмбеддинг                        |

---

## 4. Структура проекта

```
multimodal-rag/
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── api/
│   │   │   ├── search.py        # /search, /ask endpoints
│   │   │   ├── files.py         # /files, /status endpoints
│   │   │   └── ws.py            # WebSocket streaming
│   │   ├── indexer/
│   │   │   ├── watcher.py       # Watchdog service
│   │   │   ├── parsers/
│   │   │   │   ├── pdf.py
│   │   │   │   ├── audio.py
│   │   │   │   ├── image.py
│   │   │   │   ├── code.py
│   │   │   │   └── office.py
│   │   │   ├── chunker.py
│   │   │   └── embedder.py
│   │   ├── rag/
│   │   │   ├── pipeline.py      # LlamaIndex query engine
│   │   │   ├── reranker.py      # Cross-encoder
│   │   │   └── prompts.py       # System prompts
│   │   ├── db/
│   │   │   ├── models.py        # SQLAlchemy models
│   │   │   └── crud.py
│   │   └── tasks/
│   │       └── celery_app.py    # Celery + задачи индексации
│   └── tests/
│
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── SearchBar.tsx
│   │   │   ├── ResultCard.tsx    # Карточка с превью файла
│   │   │   ├── AnswerStream.tsx  # Потоковый вывод LLM
│   │   │   ├── FileBrowser.tsx   # Браузер проиндексированных файлов
│   │   │   └── IndexStatus.tsx   # Прогресс индексации
│   │   └── hooks/
│   │       ├── useSearch.ts
│   │       └── useIndexing.ts
│   └── nginx.conf
│
├── volumes/
│   ├── qdrant_data/
│   ├── sqlite_data/
│   ├── ollama_models/
│   └── redis_data/
│
└── scripts/
    ├── init-models.sh           # Скачать модели Ollama при первом запуске
    └── reindex.sh               # Полная переиндексация
```

---

## 5. Docker Compose

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
    # Для CPU-only: убрать deploy.resources
    # Для GPU (NVIDIA): раскомментировать ниже
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - ./volumes/qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
    environment:
      QDRANT__SERVICE__GRPC_PORT: 6334
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
      - ${INDEX_PATHS}:/mnt/indexed:ro   # Папки для индексации (read-only)
    environment:
      OLLAMA_HOST: http://ollama:11434
      QDRANT_HOST: qdrant
      QDRANT_PORT: 6333
      REDIS_URL: redis://redis:6379/0
      LLM_MODEL: qwen2.5:3b
      EMBED_MODEL: nomic-embed-text
      DATABASE_URL: sqlite:////app/data/metadata.db
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
      OLLAMA_HOST: http://ollama:11434
      QDRANT_HOST: qdrant
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - redis
      - ollama
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
```
INDEX_PATHS=/c/Users/alex/Documents:/d/Projects:/d/Photos
```

---

## 6. Web-интерфейс (функциональные требования)

### Главный экран
- Поисковая строка с автодополнением (поиск по именам файлов)
- Переключатель режима: **Семантический поиск** / **Вопрос-ответ (RAG)**
- Фильтры: тип файла, дата изменения, директория

### Результаты поиска
- Карточка файла: иконка типа, путь, дата, релевантный сниппет с подсветкой
- Клик → открытие файла в нативном приложении (протокол `file://`)
- Превью: PDF (первые страницы), изображение, аудиоплеер, код с подсветкой

### Режим RAG (вопрос-ответ)
- Стриминговый вывод ответа с эффектом печатания
- Блок "Источники" под ответом: до 5 файлов с кратким сниппетом
- Кнопка "Ещё источников" → развернуть полный список

### Панель индексации
- Прогресс-бар текущей индексации
- Статистика: файлов проиндексировано / всего / с ошибками
- Кнопки: "Переиндексировать всё", "Добавить директорию"
- Лог последних событий (новые файлы, ошибки парсинга)

### Настройки
- Список наблюдаемых директорий (добавить/удалить)
- Выбор LLM-модели из доступных в Ollama
- Параметры чанкинга (размер, перекрытие)
- Фильтр расширений файлов для индексации

---

## 7. Оптимизация для слабого железа

### RAM
- Qdrant: `on_disk_payload: true` + scalar quantization INT8 → экономия 4× по RAM
- Ollama: модели выгружаются через 5 минут бездействия (`OLLAMA_KEEP_ALIVE=5m`)
- Celery: `concurrency=1–2`, не больше одного embedding-запроса параллельно
- SQLite WAL-mode для concurrent reads без блокировок

### CPU
- Ollama использует `llama.cpp` с оптимизациями AVX2/AVX512
- faster-whisper: модель `tiny` (~39 MB), работает реально быстро даже на CPU
- EasyOCR: детектор `CRAFT` выключить, использовать только `easyocr.Reader` с `detail=0`
- Пакетный эмбеддинг: собирать чанки батчами по 32, не поштучно

### Диск
- Индексировать только при изменении (file hash + mtime в SQLite)
- Исключения из индексации: `.git`, `node_modules`, `__pycache__`, системные директории
- Qdrant хранит векторы в mmap-файлах — SSD обязателен для приемлемой скорости

### Первый запуск
```bash
# 1. Скачать модели (один раз, ~5 GB суммарно)
./scripts/init-models.sh

# 2. Запустить всё
docker compose up -d

# 3. Первичная индексация (фоново, не блокирует интерфейс)
# Watchdog автоматически обнаружит файлы при монтировании директорий
```

---

## 8. API-эндпоинты (FastAPI)

```
GET  /api/health                     — статус всех сервисов
POST /api/search                     — семантический поиск (top-K)
POST /api/ask                        — RAG-запрос (стриминг через SSE)
GET  /api/files                      — список проиндексированных файлов
GET  /api/files/{id}/preview         — превью файла
GET  /api/index/status               — статус индексации
POST /api/index/trigger              — запустить (пере)индексацию
POST /api/index/add-path             — добавить директорию
GET  /api/settings                   — текущие настройки
PUT  /api/settings                   — обновить настройки
```

Пример тела запроса `/api/ask`:
```json
{
  "query": "Где у меня хранится контракт с ООО Рога и Копыта?",
  "filters": {
    "file_types": ["pdf", "docx"],
    "date_after": "2024-01-01"
  },
  "top_k": 5,
  "stream": true
}
```

---

## 9. Фазы разработки

### Фаза 1 — Ядро (2–3 недели)
- Docker Compose с Qdrant + Ollama + Redis
- Парсеры: PDF, TXT, MD, DOCX
- Текстовый эмбеддинг + запись в Qdrant
- FastAPI: `/search` и `/ask` (без стриминга)
- Простой React UI: строка поиска + список результатов

### Фаза 2 — Мультимодальность (2 недели)
- Аудио: faster-whisper
- Изображения: EasyOCR + CLIP
- Видео: извлечение аудио + кадров
- Watchdog: инкрементальная индексация

### Фаза 3 — UX и качество (1–2 недели)
- Стриминг ответа LLM через WebSocket
- Cross-encoder reranker
- Превью файлов в интерфейсе
- Панель статуса индексации
- Фильтры поиска

### Фаза 4 — Продакшн-фичи (по желанию)
- Гибридный поиск: BM25 + семантика (Qdrant Sparse + Dense)
- Conversation history (память диалога)
- Экспорт результатов в Markdown
- Мобильный PWA
- Автообновление моделей Ollama

---

## 10. Альтернативные компоненты (если нужна замена)

| Компонент        | Основной выбор          | Альтернативы                                  |
|------------------|-------------------------|-----------------------------------------------|
| LLM inference    | Ollama                  | llama.cpp сервер, LM Studio API (локально)    |
| Векторная БД     | Qdrant                  | ChromaDB (проще, но медленнее), Weaviate       |
| Embeddings       | nomic-embed-text        | all-MiniLM-L6-v2 (HuggingFace, без Ollama)   |
| OCR              | EasyOCR                 | Tesseract 5 (медленнее, но стабильнее)        |
| RAG-фреймворк    | LlamaIndex              | LangChain (больше экосистема, но тяжелее)     |
| Очередь задач    | Celery + Redis          | ARQ (async, без Redis), простой asyncio queue |
| Frontend         | React + Vite            | SvelteKit (легче), plain HTML + HTMX           |

---

## 11. Безопасность и приватность

- Все данные хранятся локально, нет исходящих сетевых запросов
- Ollama, Qdrant, Redis доступны только внутри Docker-сети (не публикуются наружу)
- Frontend и API доступны только на `localhost` по умолчанию
- Файлы монтируются только для чтения (`ro`) — система не изменяет оригиналы
- При необходимости доступа с других устройств в сети: Nginx reverse proxy с Basic Auth

---

*Документ сгенерирован как стартовая точка для разработки. Версии библиотек следует зафиксировать в `pyproject.toml` и `package.json` после выбора конкретного окружения.*
