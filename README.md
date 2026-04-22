# FleshRAG MVP

Локальный multimodal RAG для файлов с `search`, `ask`, диалогами, предпросмотром файлов и admin console.

## Быстрый старт

### 1. Подготовьте `.env`

Скопируйте [.env.example](E:/YD/projects/fleshrag/.env.example) в `.env`.

Самый быстрый сценарий для MVP:

```env
DEFAULT_PROVIDER=cloud
NEURALDEEP_API_KEY=
INDEX_ROOT_HOST=./test_data
INDEX_ROOT_CONTAINER=/mnt/indexed
INDEX_PATHS=/mnt/indexed
```

Что это даёт:
- если `NEURALDEEP_API_KEY` пустой, приложение можно запустить и потом переключиться в `local`;
- для первой проверки будет индексироваться `./test_data`.

Для cloud-режима:
- впишите `NEURALDEEP_API_KEY`.

### 2. Поднимите сервисы

```bash
docker compose up --build
```

### 3. Проверьте readiness

- UI: [http://localhost:3000](http://localhost:3000)
- Health: [http://localhost:8000/api/health](http://localhost:8000/api/health)
- Ready: [http://localhost:8000/api/ready](http://localhost:8000/api/ready)

`/api/ready` должен вернуть:
- `database: ok`
- `qdrant: ok`
- `provider: cloud-configured` или `local-fallback`

## Первый сценарий проверки

### 1. Откройте Admin

В UI перейдите в `Admin`.

Там можно:
- увидеть текущий провайдер,
- посмотреть budget/status,
- выполнить `Test connection`,
- переключить `cloud/local`,
- запустить `Reindex all`.

### 2. Запустите переиндексацию

Нажмите `Reindex all`.

Для быстрого MVP это поставит в очередь индексацию путей из `INDEX_PATHS`.

### 3. Проверьте Search

Перейдите во вкладку `Search`:
- задайте простой запрос по содержимому файлов из `test_data`.

### 4. Проверьте Ask

Перейдите во вкладку `Ask`:
- задайте вопрос по тем же документам,
- убедитесь, что приходят ответ и источники.

### 5. Проверьте Library

Во вкладке `Library`:
- отфильтруйте файлы,
- откройте preview.

## Как работает выбор провайдера

- `cloud` используется по умолчанию, если есть `NEURALDEEP_API_KEY`;
- если ключ не задан, backend считает систему готовой в режиме `local-fallback`;
- фактический provider можно переключать из `Admin`.

## Если что-то не работает

### `Provider unavailable`

Причины:
- не запущен `ollama` для local режима;
- не задан `NEURALDEEP_API_KEY` для cloud режима.

Что делать:
- для local: убедитесь, что `docker compose up` поднял `ollama`;
- для cloud: пропишите `NEURALDEEP_API_KEY`.

### `/api/ready` возвращает `degraded`

Проверьте:
- `docker compose ps`
- логи `backend`, `worker`, `qdrant`, `ollama`

### В Search ничего не находится

Проверьте:
- была ли запущена `Reindex all`
- индексируется ли путь из `INDEX_PATHS`
- есть ли файлы внутри `INDEX_ROOT_HOST`

## Полезные команды

```bash
docker compose up --build
docker compose ps
docker compose logs backend
docker compose logs worker
docker compose logs ollama
python tests/smoke_tests.py
```
