# KODA: FleshRAG — Multimodal RAG для локального семантического поиска

## Обзор проекта

**FleshRAG** — это локальная мультимодальная система RAG (Retrieval-Augmented Generation) для семантического поиска и ответов на вопросы по содержимому файлов на домашнем ПК. Система работает полностью офлайн, без отправки данных во внешние сервисы, и оптимизирована для слабого железа (CPU-only, 8–16 GB RAM).

**Основные возможности:**
- Индексация документов (PDF, DOCX, XLSX, PPTX), изображений, аудио, видео и исходного кода
- Семантический поиск по содержимому файлов на естественном языке
- Режим вопрос-ответ (RAG) с генерацией ответа через локальную LLM
- Инкрементальная индексация новых и изменённых файлов через Watchdog
- Превью файлов и ссылки на оригиналы

**Архитектура:**
- Фронтенд: React 18 + Vite + Tailwind CSS
- Бэкенд: FastAPI + LlamaIndex + Celery
- Модели: Ollama (Qwen2.5 3B, nomic-embed-text)
- Векторная БД: Qdrant
- Очередь задач: Redis
- Метаданные: SQLite

---

## Структура проекта

```
E:\yd\projects\fleshrag\
├── docker-compose.yml          # Оркестрация всех сервисов
├── .env / .env.example         # Переменные окружения (пути для индексации)
├── TZ_Multimodal_RAG.md        # Полное техническое задание
│
├── backend/                    # Python-бэкенд (FastAPI)
│   ├── Dockerfile
│   ├── pyproject.toml          # Зависимости (FastAPI, LlamaIndex, Celery и др.)
│   └── app/
│       ├── main.py             # Точка входа FastAPI, запуск watchdog
│       ├── config.py           # Pydantic-настройки из окружения
│       ├── api/
│       │   ├── search.py       # Эндпоинты /api/search и /api/ask
│       │   ├── files.py        # Эндпоинты для работы с файлами
│       │   └── index.py        # Эндпоинты статуса и управления индексацией
│       ├── indexer/
│       │   ├── watchdog_service.py  # Watchdog для мониторинга файлов
│       │   ├── chunker.py      # Разбиение текста на чанки
│       │   ├── embedder.py     # Генерация эмбеддингов через Ollama
│       │   ├── watcher.py      # Логика наблюдения за директориями
│       │   └── parsers/        # Парсеры различных форматов
│       │       ├── audio.py    # Аудио (faster-whisper)
│       │       ├── image.py    # Изображения (EasyOCR)
│       │       ├── office.py   # Office-документы
│       │       ├── pdf.py      # PDF (PyMuPDF)
│       │       └── video.py    # Видео
│       ├── rag/
│       │   ├── pipeline.py     # Пайплайн поиска и RAG (LlamaIndex + Qdrant)
│       │   ├── reranker.py     # Cross-encoder переранжирование
│       │   └── prompts.py      # Системные промпты
│       ├── db/
│       │   ├── models.py       # SQLAlchemy-модели
│       │   └── crud.py         # Операции с БД
│       └── tasks/
│           └── celery_app.py   # Celery-приложение и задачи индексации
│
├── frontend/                   # React-приложение
│   ├── Dockerfile
│   ├── package.json            # Зависимости (React, Vite, Tailwind)
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── App.tsx             # Главный компонент (поиск / вопрос-ответ)
│       ├── main.tsx            # Точка входа
│       ├── index.css           # Глобальные стили
│       ├── components/
│       │   ├── SearchBar.tsx   # Поисковая строка
│       │   └── ResultCard.tsx  # Карточка результата
│       └── hooks/              # React-хуки
│
├── scripts/
│   ├── init-models.sh          # Скачивание моделей Ollama
│   └── reindex.sh              # Полная переиндексация
│
├── test_data/                  # Тестовые данные для индексации
│   ├── readme.txt
│   └── test.md
│
└── volumes/                    # Docker-volumes для персистентности
    ├── ollama_models/          # Скачанные модели
    ├── qdrant_data/            # Векторная база данных
    ├── redis_data/             # Данные Redis
    └── sqlite_data/            # SQLite БД метаданных
```

---

## Сборка и запуск

### Предварительные требования
- Docker + Docker Compose
- Windows 11 / WSL2 или Linux
- ~5 GB свободного места для моделей

### Основные команды

```bash
# 1. Настроить пути для индексации (скопировать .env.example → .env и отредактировать)
cp .env.example .env
# В .env указать: INDEX_PATHS=/c/Users/alex/Documents:/d/Projects

# 2. Запустить все сервисы
docker compose up -d

# 3. Скачать модели Ollama (при первом запуске)
./scripts/init-models.sh

# 4. Проверить статус
curl http://localhost:8000/api/health
```

### Доступ к сервисам
| Сервис | URL |
|--------|-----|
| Веб-интерфейс | http://localhost:3000 |
| API (FastAPI) | http://localhost:8000 |
| Qdrant Dashboard | http://localhost:6333 |
| Ollama API | http://localhost:11434 |

### Перезапуск / остановка
```bash
docker compose restart backend
docker compose logs -f worker
docker compose down
```

### Полная переиндексация
```bash
./scripts/reindex.sh
```

### Разработка фронтенда (без Docker)
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
npm run build      # production-сборка
```

### Разработка бэкенда (без Docker)
```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Технологический стек

### Бэкенд (Python 3.11+)
| Компонент | Технология |
|-----------|------------|
| API-фреймворк | FastAPI + uvicorn |
| RAG-оркестрация | LlamaIndex 0.12+ |
| LLM / Embeddings | Ollama (qwen2.5:3b, nomic-embed-text) |
| Векторная БД | Qdrant |
| Очередь задач | Celery + Redis |
| ORM | SQLAlchemy + Alembic |
| Мониторинг файлов | Watchdog |
| OCR | EasyOCR |
| Аудио | faster-whisper |
| PDF | PyMuPDF |
| Office | python-docx, openpyxl, python-pptx |
| Reranker | sentence-transformers (cross-encoder) |

### Фронтенд
| Компонент | Технология |
|-----------|------------|
| UI-фреймворк | React 18 |
| Сборщик | Vite |
| Стили | Tailwind CSS v3 |
| Язык | TypeScript |

### Инфраструктура (Docker)
- `ollama` — inference LLM и embeddings
- `qdrant` — векторная БД
- `redis` — брокер Celery
- `backend` — FastAPI-сервер
- `worker` — Celery-worker для индексации
- `frontend` — nginx со статическим React

---

## Правила разработки

### Стиль кода
- Бэкенд: стандартный стиль Python (PEP 8). В проекте подключён `ruff` для линтинга.
- Фронтенд: TypeScript с строгой типизацией. Компоненты — функциональные с хуками.
- Импорты: относительные внутри пакетов (`from app.config import settings`).

### Архитектурные решения
- **Async/await** везде, где возможно (FastAPI эндпоинты, запросы к Qdrant).
- **Celery** для фоновой индексации — API не блокируется при обработке файлов.
- **Watchdog** запускается в отдельном daemon-потоке при старте FastAPI (`@app.on_event("startup")`).
- **Read-only монтирование** индексируемых директорий (`:ro` в Docker) — система не изменяет оригиналы.
- **Chunking**: размер чанка 512 токенов, перекрытие 64 токена (SentenceSplitter).

### Расширение функциональности
- Новый парсер: добавить модуль в `backend/app/indexer/parsers/`, реализовать функцию извлечения текста.
- Новый API-эндпоинт: создать файл в `backend/app/api/` и подключить роутер в `main.py`.
- Новый компонент UI: создать `.tsx` в `frontend/src/components/`.

### Конфигурация
Все настройки централизованы в `backend/app/config.py` (Pydantic Settings) и переопределяются через переменные окружения:
- `OLLAMA_HOST` — хост Ollama
- `QDRANT_HOST` / `QDRANT_PORT` — подключение к Qdrant
- `REDIS_URL` — брокер Celery
- `LLM_MODEL` / `EMBED_MODEL` — модели Ollama
- `INDEX_PATHS` — пути для индексации (через `:`)
- `CHUNK_SIZE` / `CHUNK_OVERLAP` — параметры чанкинга
- `TOP_K_SEARCH` / `TOP_K_RERANK` — параметры поиска

---

## Ключевые файлы

| Файл | Назначение |
|------|------------|
| `TZ_Multimodal_RAG.md` | Полное техническое задание с описанием всех фаз, API и архитектуры |
| `docker-compose.yml` | Определение всех сервисов Docker, их зависимостей и volumes |
| `backend/pyproject.toml` | Python-зависимости проекта |
| `backend/app/main.py` | Точка входа FastAPI, CORS, запуск watchdog |
| `backend/app/config.py` | Центральная конфигурация через Pydantic Settings |
| `backend/app/rag/pipeline.py` | Ядро RAG: эмбеддинги, Qdrant-поиск, генерация ответа LLM |
| `backend/app/indexer/watchdog_service.py` | Мониторинг файловой системы и постановка задач в Celery |
| `backend/app/tasks/celery_app.py` | Определение Celery-задач для фоновой индексации |
| `frontend/src/App.tsx` | Главный UI: переключение режимов поиск/вопрос-ответ |
| `scripts/init-models.sh` | Скрипт первоначальной загрузки моделей в Ollama |

---

## Статус проекта

Проект находится в начальной фазе разработки (Фаза 1 по ТЗ). Реализовано:
- ✅ Docker Compose с Qdrant, Ollama, Redis, бэкендом и фронтендом
- ✅ Базовая структура FastAPI с эндпоинтами `/api/search` и `/api/ask`
- ✅ Интеграция LlamaIndex + Ollama embeddings + Qdrant
- ✅ Простой React-UI с поисковой строкой и переключением режимов
- ✅ Watchdog для мониторинга файлов
- ✅ Celery-worker для фоновой индексации

В процессе / планируется:
- 🔄 WebSocket/SSE стриминг ответа LLM
- 🔄 Cross-encoder reranker
- 🔄 Превью файлов в UI
- 🔄 Парсеры аудио, видео, изображений
- 🔄 Панель статуса индексации
