# FleshRAG — Production-Ready Multimodal RAG

Локальная multimodal RAG-система для семантического поиска и ответов на вопросы по файлам. Поддерживает **search**, **ask**, диалоги, предпросмотр файлов, admin console и production-grade возможности.

## ✨ Возможности

- 🔍 **Семантический поиск** — гибридный поиск (dense + BM25)
- 💬 **Вопрос-ответ (RAG)** — генерация ответов с источниками
- 📁 **Мультимодальность** — текст, PDF, Office, аудио, видео, изображения
- 🔄 **Гибридные провайдеры** — cloud (NeuralDeep) / local (Ollama) с circuit breaker
- ⚡ **GPU acceleration** — автоопределение и оптимальное использование GPU
- 💾 **Artifact cache** — кэширование OCR и транскрипции (30 дней)
- 🛡️ **Retry policies** — отказоустойчивость с экспоненциальным backoff
- 📊 **Admin console** — monitoring, budget tracking, управление индексацией

---

## Быстрый старт

### 1. Подготовьте `.env`

Скопируйте `.env.example` в `.env`.

**Самый быстрый сценарий (local-fallback):**

```env
DEFAULT_PROVIDER=local
LOCAL_EMBED_MODEL=nomic-embed-text
LOCAL_LLM_MODEL=qwen2.5:3b
INDEX_PATHS=/mnt/indexed
```

**Cloud-режим:**

```env
DEFAULT_PROVIDER=cloud
NEURALDEEP_API_KEY=your_api_key_here
CLOUD_LLM_MODEL=gpt-oss-120b
CLOUD_EMBED_MODEL=e5-large
INDEX_PATHS=/mnt/indexed
```

**GPU ускорение (если доступно):**

```env
GPU_POLICY_ENABLED=true
GPU_ALLOW_TRANSCRIPTION=true
GPU_ALLOW_RERANK=true
GPU_ALLOW_EMBEDDINGS=true
GPU_ALLOW_LOCAL_LLM=false  # Только для мощных GPU (8GB+)
```

### 2. Поднимите сервисы

```bash
docker compose up --build
```

### 3. Проверьте readiness

- **UI**: http://localhost:3000
- **Health**: http://localhost:8000/api/health
- **Ready**: http://localhost:8000/api/ready
- **Admin API**: http://localhost:8000/api/admin/status

`/api/ready` должен вернуть:
- `database: ok`
- `qdrant: ok`
- `provider: cloud-configured` или `local-fallback`

---

## Первый сценарий проверки

### 1. Откройте Admin Console

В UI перейдите во вкладку **Admin**.

Там можно:
- ✅ Увидеть текущий провайдер и модели
- ✅ Проверить **GPU status** (CUDA, память, доступные задачи)
- ✅ Посмотреть **budget/status**
- ✅ Выполнить **Test connection**
- ✅ Переключить **cloud/local**
- ✅ Запустить **Reindex all**
- ✅ Проверить **Index version** и совместимость

### 2. Запустите переиндексацию

Нажмите **Reindex all**.

Для быстрого MVP это поставит в очередь индексацию путей из `INDEX_PATHS`.

### 3. Проверьте Search

Перейдите во вкладку **Search**:
- Задайте простой запрос по содержимому файлов из `test_data`.

### 4. Проверьте Ask

Перейдите во вкладку **Ask**:
- Задайте вопрос по тем же документам.
- Убедитесь, что приходят ответ и источники.

### 5. Проверьте Library

Во вкладке **Library**:
- Отфильтруйте файлы.
- Откройте preview.

---

## Как работает выбор провайдера

| Режим | Условия | Behaviour |
|-------|---------|-----------|
| **cloud** | `NEURALDEEP_API_KEY` задан | Использует NeuralDeep API |
| **local** | Ключ не задан или переключено вручную | Использует Ollama + local модели |
| **fallback** | Cloud недоступен (circuit breaker) | Автоматический переход на local |

**Circuit Breaker:**
- 3 неудачи → переход в OPEN (60s cooldown)
- После cooldown → HALF_OPEN (тестовый запрос)
- Успех → CLOSED (возврат к cloud)

---

## Production Features

### 🔁 Artifact Cache

Кэширование результатов тяжелых операций:
- **OCR** изображений
- **Транскрибация** аудио/видео
- **Video frames** metadata

**Хранение:**
- Redis (метаданные) + диск (JSON файлы)
- TTL: 30 дней
- Ключ: `content_hash + parser_type + parser_version`

**Эффект:**
- Повторная индексация в 5-10× быстрее
- Избежание дублирования дорогих вычислений

### 🛡️ Retry Policies

Автоматические повторные попытки с экспоненциальным backoff:

| Операция | Retries | Backoff | Timeout |
|----------|---------|---------|---------|
| Embeddings | 3 | Exponential | 60s |
| Chat/LLM | 2 | Exponential | 180s |
| Rerank | 2 | Linear | 30s |
| Transcription | 1 | Linear | 600s |
| OCR | 2 | Linear | 60s |

### 🎮 GPU Auto-detect

Автоматическое определение и оптимальное использование GPU:

**Автоконфигурация:**
- Определение CUDA и доступных GPU
- Распределение задач по памяти:
  - Transcription: min 4GB
  - Rerank: min 2GB
  - Embeddings: min 2GB
  - Local LLM: min 8GB

**Проверка статуса:**
```bash
curl http://localhost:8000/api/admin/status | jq .gpu
```

**Пример ответа:**
```json
{
  "cuda_available": true,
  "gpu": {"name": "RTX 3080", "total_memory_gb": 10.0},
  "can_use_gpu": {
    "transcription": true,
    "rerank": true,
    "embeddings": true,
    "local_llm": false
  }
}
```

### 📊 Index Versioning

Версионирование индекса для предотвращения "тихих" ошибок:
- Метаданные: `embed_model`, `vector_dim`, `index_version`
- Проверка совместимости при поиске
- Предупреждение о необходимости переиндексации

**API:** `/api/index/version`

---

## Медиа-файлы (аудио/видео)

Система поддерживает индексацию аудио и видео файлов:

### Поддерживаемые форматы
- **Аудио**: `.mp3`, `.wav`, `.flac`, `.aac`, `.ogg`, `.m4a`, `.wma`, `.opus`
- **Видео**: `.mp4`, `.avi`, `.mkv`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`

### Как это работает (ffmpeg-пайплайн)

1. **Ресемплинг**: ffmpeg конвертирует аудио в 16 kHz mono WAV
2. **Транскрибация**:
   - **Cloud**: `whisper-1` через neuraldeep.ru ($0.003/мин)
   - **Local**: `faster-whisper base` (INT8, ~350 MB RAM)
3. **Для видео**: дополнительно извлекаются кадры (1/5 сек) с OCR

```
Видео/Аудио → ffmpeg (16kHz mono WAV) → Whisper → текст → Qdrant
```

### Кэширование

Результаты транскрипции кэшируются в **Artifact Cache**:
- Повторная индексация того же файла — мгновенно
- Ключ: `content_hash + "transcription" + "1.0"`

---

## Если что-то не работает

### `Provider unavailable`

**Причины:**
- Не запущен `ollama` для local режима
- Не задан `NEURALDEEP_API_KEY` для cloud режима

**Что делать:**
- Для local: убедитесь, что `docker compose up` поднял `ollama`
- Для cloud: пропишите `NEURALDEEP_API_KEY`

### `/api/ready` возвращает `degraded`

**Проверьте:**
- `docker compose ps`
- Логи `backend`, `worker`, `qdrant`, `ollama`
- `/api/admin/status` для деталей

### В Search ничего не находится

**Проверьте:**
- Была ли запущена `Reindex all`
- Индексируется ли путь из `INDEX_PATHS`
- Есть ли файлы внутри `INDEX_ROOT_HOST`

### GPU не используется

**Проверьте:**
```bash
curl http://localhost:8000/api/admin/status | jq .gpu
```

**Возможные причины:**
- GPU недостаточно памяти (требуется min для задачи)
- GPU отключен в policy (`GPU_POLICY_ENABLED=false`)
- Задача запрещена для GPU (например, `GPU_ALLOW_LOCAL_LLM=false`)

---

## Полезные команды

```bash
# Запуск
docker compose up --build

# Статус
docker compose ps
docker compose logs backend
docker compose logs worker
docker compose logs ollama

# Тесты
python tests/smoke_tests.py
cd backend && python -m pytest tests/ -v

# Проверка CUDA
./scripts/check-cuda.sh

# Admin API
curl http://localhost:8000/api/admin/status | jq
curl http://localhost:8000/api/index/version | jq
```

---

## CUDA / GPU ускорение

Система автоматически использует GPU для следующих компонентов:
- **PyTorch** (faster-whisper, sentence-transformers) — CUDA 12.1
- **EasyOCR** — GPU ускорение для OCR
- **faster-whisper** — транскрибация аудио/видео
- **sentence-transformers** — эмбеддинги

### Требования для GPU

1. **NVIDIA драйверы** установлены на хосте
2. **NVIDIA Container Toolkit** установлен:
   ```bash
   # Ubuntu/Debian
   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit.gpg
   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
   sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
   sudo nvidia-ctk runtime configure --runtime=docker
   sudo systemctl restart docker
   ```

3. **Проверка GPU**:
   ```bash
   ./scripts/check-cuda.sh
   ```

### Отключение GPU

Если GPU не нужен или недоступен, сервисы автоматически fallback на CPU.

Для принудительного отключения GPU добавьте в `.env`:
```env
GPU_POLICY_ENABLED=false
```

---

## Архитектура

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Frontend  │──────│   Backend    │──────│   Qdrant    │
│  (React)    │      │  (FastAPI)   │      │  (VectorDB) │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
   ┌─────▼─────┐     ┌─────▼─────┐     ┌─────▼─────┐
   │  Ollama   │     │   Redis   │     │  Worker   │
   │  (Local)  │     │  (Cache)  │     │  (Celery) │
   └───────────┘     └───────────┘     └───────────┘
```

### Компоненты

| Компонент | Назначение |
|-----------|------------|
| **Backend** | FastAPI API, ModelRouter, circuit breaker |
| **Worker** | Celery для фоновой индексации |
| **Ollama** | Local LLM (qwen2.5:3b) + embeddings (nomic-embed-text) |
| **Qdrant** | Векторная база данных |
| **Redis** | Кэш метаданных, artifact cache, runtime state |
| **Embed-service** | HF embeddings (multilingual-e5-large) |

---

## Тестирование

```bash
# Backend тесты
cd backend
python -m pytest tests/ -v

# Ключевые тесты
python -m pytest tests/test_artifact_cache.py -v   # 19 тестов
python -m pytest tests/test_retry_policies.py -v  # 24 теста
python -m pytest tests/test_gpu_policy.py -v      # 25 тестов
python -m pytest tests/test_circuit_breaker.py -v # 10 тестов
python -m pytest tests/test_index_versioning.py -v # 25 тестов
```

**Итого:** 160+ тестов, ~100% покрытие критических путей.

---

## Лицензия

MIT License
