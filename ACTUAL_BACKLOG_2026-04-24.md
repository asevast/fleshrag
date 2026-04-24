# FleshRAG Actual Backlog

**Дата актуализации:** 2026-04-24  
**Основа:** [README.md](E:/YD/projects/fleshrag/README.md), [TZ_Multimodal_RAG_v2.2.md](E:/YD/projects/fleshrag/TZ_Multimodal_RAG_v2.2.md), [TZ_Multimodal_RAG_v2.3.md](E:/YD/projects/fleshrag/TZ_Multimodal_RAG_v2.3.md) и текущее состояние репозитория.

## Контекст

Проект уже вышел за рамки простого MVP:
- появился `embed-service`,
- `docker-compose.yml` ориентирован на GPU/CUDA и более зрелый runtime,
- README описывает richer flow и мультимодальность,
- в backend появились `ModelRouter`, `admin API`, провайдеры `cloud/local`.

Но кодовая база частично рассинхронизирована:
- часть runtime и документации уже живёт в новой архитектуре,
- часть backend/frontend всё ещё работает по старой локальной схеме,
- тесты частично проверяют уже не тот контракт.

Поэтому дальше важнее не “добавлять ещё фичи”, а сначала выровнять архитектурную правду проекта.

---

## Critical

### 1. Свести `config + compose + router + pipeline` к одной архитектуре

**Проблема**
- [backend/app/config.py](E:/YD/projects/fleshrag/backend/app/config.py) не соответствует текущему `docker-compose.yml`.
- [backend/app/rag/pipeline.py](E:/YD/projects/fleshrag/backend/app/rag/pipeline.py) всё ещё использует прямой `Ollama`.
- [backend/app/indexer/embedder.py](E:/YD/projects/fleshrag/backend/app/indexer/embedder.py) тоже работает по старой схеме.
- [backend/app/models/router.py](E:/YD/projects/fleshrag/backend/app/models/router.py) существует, но не стал центральной точкой системы.

**Что сделать**
- Привести `config.py` к текущим env:
  - `DEFAULT_PROVIDER`
  - `NEURALDEEP_*`
  - `LOCAL_*`
  - `CLOUD_*`
  - `INDEX_PATHS`
  - `LLM_*`
- Перевести `pipeline.py` на `ModelRouter`.
- Перевести `embedder.py` на provider-aware embeddings.
- Удалить или изолировать legacy-путь прямого `Ollama`, если он больше не нужен.

**Результат**
- Один реальный execution path для `search`, `ask`, `embed`, `rerank`.

### 2. Решить роль `embed-service`

**Проблема**
- `embed-service` уже есть в runtime, но backend не использует его как основной слой embeddings.
- Непонятно, он обязательный, опциональный или fallback-only.

**Что сделать**
- Зафиксировать архитектурное решение:
  - `embed-service` как основной локальный embeddings backend
  - или `embed-service` как optional acceleration layer
- Интегрировать это решение в:
  - [backend/app/models/providers/local.py](E:/YD/projects/fleshrag/backend/app/models/providers/local.py)
  - [backend/app/indexer/embedder.py](E:/YD/projects/fleshrag/backend/app/indexer/embedder.py)
  - [backend/app/api/admin.py](E:/YD/projects/fleshrag/backend/app/api/admin.py)
  - README и `.env.example`

**Результат**
- Понятный и единый локальный путь эмбеддингов без “двойной архитектуры”.

### 3. Синхронизировать frontend с текущей backend-архитектурой

**Проблема**
- [frontend/src/App.tsx](E:/YD/projects/fleshrag/frontend/src/App.tsx) сейчас проще, чем описано в README.
- В репозитории есть admin-компоненты, dialogs-компоненты и richer UX-слой, но текущий app shell их не отражает полностью.

**Что сделать**
- Выбрать один актуальный frontend shell.
- Вернуть/собрать навигацию:
  - `Search`
  - `Ask`
  - `Library`
  - `Dialogs`
  - `Admin`
- Проверить, что UI реально использует текущие admin/search/index endpoints.

**Результат**
- UI соответствует README и текущему product scope.

### 4. Переписать health/ready/tests под реальный контракт

**Проблема**
- [backend/tests/test_integration.py](E:/YD/projects/fleshrag/backend/tests/test_integration.py) ожидает формат `health`, который сейчас не совпадает с кодом.
- Smoke и integration слой уже не полностью синхронны с API.

**Что сделать**
- Обновить `health` и `ready` контракты.
- Синхронизировать:
  - [backend/tests/test_integration.py](E:/YD/projects/fleshrag/backend/tests/test_integration.py)
  - [backend/tests/test_smoke.py](E:/YD/projects/fleshrag/backend/tests/test_smoke.py)
  - [tests/smoke_tests.py](E:/YD/projects/fleshrag/tests/smoke_tests.py)
- Зафиксировать единый сценарий:
  - startup
  - readiness
  - indexing
  - search
  - ask
  - admin

**Результат**
- Тесты снова отражают правду системы.

---

## Next

### 5. Circuit Breaker для cloud provider

**Основа:** TZ 2.2 / 2.3

**Что сделать**
- Добавить `app/models/circuit_breaker.py`
- Внедрить threshold + cooldown
- Не переключать `cloud -> local` по первой ошибке
- Добавить health-check перед возвратом на cloud

**Файлы**
- [backend/app/models/router.py](E:/YD/projects/fleshrag/backend/app/models/router.py)
- `backend/app/models/circuit_breaker.py`
- возможно `backend/app/api/admin.py`

**Результат**
- Переходы между провайдерами становятся предсказуемыми и устойчивыми.

### 6. Идемпотентная индексация и fingerprint/chunk id

**Проблема**
- Сейчас высокий риск дублей и непредсказуемого переиндексирования.

**Что сделать**
- Ввести fingerprint файла:
  - path
  - size
  - mtime
  - content_hash
- Генерировать стабильный `chunk_id`
- Обновлять чанки при переиндексации, а не плодить новые

**Файлы**
- [backend/app/indexer/watcher.py](E:/YD/projects/fleshrag/backend/app/indexer/watcher.py)
- [backend/app/indexer/embedder.py](E:/YD/projects/fleshrag/backend/app/indexer/embedder.py)
- [backend/app/db/models.py](E:/YD/projects/fleshrag/backend/app/db/models.py)

**Результат**
- Индексирование становится детерминированным.

### 7. Версионирование индекса

**Проблема**
- При смене embedding модели/размерности проект легко входит в “тихо сломанное” состояние.

**Что сделать**
- Добавить metadata:
  - `embed_model`
  - `vector_dim`
  - `index_version`
- Блокировать поиск при несовпадении
- Показывать `reindex required` в API/UI

**Файлы**
- [backend/app/db/models.py](E:/YD/projects/fleshrag/backend/app/db/models.py)
- [backend/app/indexer/embedder.py](E:/YD/projects/fleshrag/backend/app/indexer/embedder.py)
- [backend/app/api/admin.py](E:/YD/projects/fleshrag/backend/app/api/admin.py)
- frontend admin/search UI

**Результат**
- Система перестаёт “молча работать неправильно”.

### 8. SQLite hardening

**Основа:** TZ 2.2

**Что сделать**
- Включить:
  - `journal_mode=WAL`
  - `busy_timeout=5000`
- Проверить concurrent path:
  - backend
  - worker
  - admin/settings

**Файлы**
- [backend/app/db/models.py](E:/YD/projects/fleshrag/backend/app/db/models.py)

**Результат**
- Меньше блокировок и ошибок при конкурентной работе.

### 9. Runtime state отдельно от persistent settings

**Проблема**
- Сейчас часть runtime-смысла смешана с persistent settings.

**Что сделать**
- `system_settings` оставить для конфигурации
- runtime state вынести в Redis/in-memory:
  - active provider с учётом fallback
  - circuit breaker state
  - error streaks
  - transient health

**Результат**
- Поведение провайдера становится прозрачным и управляемым.

---

## Later

### 10. Artifact cache для OCR / transcription / frames

**Основа:** TZ 2.2 / 2.3

**Что сделать**
- Кэшировать:
  - OCR
  - transcription
  - extracted frames metadata
- Ключ: `content_hash + parser_version`

**Файлы**
- новый `backend/app/cache/artifacts.py`
- парсеры image/audio/video

**Результат**
- Значительно дешевле и быстрее повторная индексация.

### 11. Retry/timeout policies по типам операций

**Что сделать**
- Разные политики для:
  - embeddings
  - chat
  - rerank
  - transcription

**Результат**
- Устойчивость без лишних повторов дорогих операций.

### 12. GPU auto-detect и policy layer

**Проблема**
- Compose и README уже живут в GPU/CUDA-мире, но policy слой ещё не завершён.

**Что сделать**
- Автоопределение CUDA
- Явное распределение:
  - transcription
  - reranker
  - embeddings
- Не использовать GPU для local LLM на слабой карте
- Дать флаг в admin/settings

**Результат**
- GPU используется там, где даёт реальную пользу, а не создаёт нестабильность.

### 13. UX состояния из TZ 2.2/2.3

**Что сделать**
- Явно вернуть в UI/API:
  - indexing
  - fallback
  - cloud unavailable
  - reindex required
  - budget warning
- Один основной сниппет на документ
- `show more`
- modal-подтверждения для опасных действий

**Результат**
- Система становится понятнее в эксплуатации.

### 14. Мультимодальность до production-grade

**Что сделать**
- Довести audio/video/image pipeline до устойчивого состояния
- Проверить ffmpeg flow
- Улучшить preview/media traceability

**Результат**
- Мультимодальность перестаёт быть “номинальной поддержкой”.

---

## Рекомендуемый порядок работы

1. `Critical 1-4`
2. `Next 5-9`
3. `Later 10-14`

---

## Самый важный вывод

Сейчас главный риск проекта не в нехватке идей, а в рассинхроне между:
- документацией,
- runtime/config,
- backend execution path,
- frontend shell,
- тестами.

Поэтому ближайшая цель разработки:

**сначала восстановить единую архитектурную правду проекта, потом уже наращивать reliability и UX-функции из TZ 2.2/2.3.**
