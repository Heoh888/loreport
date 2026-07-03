# Архитектура Loreport

## Обзор

Loreport состоит из двух основных runtime-компонентов и набора общих библиотек:

- `loreport-api` — FastAPI-приложение, которое принимает запросы UI и webhook.
- `loreport-worker` — фоновый consumer, который выполняет agent-run для `init` / `update`.
- `backend/loreport_core` — общая логика агента, git evidence и snapshot.
- `backend/loreport_server` — серверная оболочка: API, БД, очередь, конфиг, worker.
- `web/` — React/Vite frontend.

## Deployment model

В `docker/docker-compose.yml` заложена схема:

- PostgreSQL для job history и настроек.
- RabbitMQ для очереди sync jobs.
- Один образ, который запускается в двух режимах: API и worker.
- Mounted repository доступен как `/repo`.

## Runtime flow

### Sync trigger

1. Webhook или polling замечает изменение HEAD.
2. API создаёт `SyncJob` со статусом `pending`.
3. API публикует задачу в RabbitMQ через `publish_sync_job()`.
4. Worker получает сообщение и запускает `run_loreport_agent()`.
5. Agent читает git evidence и формирует prompt-контекст.
6. До и после запуска строится snapshot каталога `loreport/`.
7. Если контент изменился, worker пишет `.last-update.json`.
8. Статус job фиксируется в PostgreSQL.

### Init

`init` использует ту же инфраструктуру, что и `update`, но предназначен для первого прохода по репозиторию и создания начального набора lore.

## Snapshot guard

Snapshot guard — критический механизм против пустых sync loops.

- Хэшируется содержимое `loreport/`.
- `.last-update.json` исключается из сравнения.
- Если snapshot до и после одинаковый, metadata не обновляется.

Это поведение явно сохранено в `backend/loreport_core/agent/runner.py` и `backend/loreport_core/git/evidence.py`.

## Storage

### PostgreSQL

Судя по коду и документам, база используется для:

- `jobs` / `SyncJob` — история sync runs.
- `settings` — не секретные настройки.
- LangGraph checkpoint storage — для agent threads в будущем/по плану.

### Repository storage

Генерируемая lore хранится прямо в репозитории:

- `REPO_PATH/loreport/`
- `REPO_PATH/loreport/.last-update.json`

## API shape

### Sync

- `POST /api/sync/trigger`
- `GET /api/sync/status`
- `GET /api/sync/history`
- `GET /api/sync/snapshot`

### Docs

- `GET /api/docs/tree`
- `GET /api/docs/content`
- `GET /api/docs/render`

### Webhooks

- `POST /webhooks/git`

### Settings

- `GET /api/settings`
- `PUT /api/settings`

## Frontend

`web/` пока содержит только scaffold на React/Vite, но уже предусмотрен SPA-режим:

- static build отдаётся из `/app/static`.
- FastAPI делает fallback на `index.html`.
- `/assets` монтируется отдельно.

## Принципиальные ограничения

- API не запускает agent jobs напрямую; он только публикует сообщения.
- Secrets остаются в env vars.
- Репозиторий — источник истины для lore, а не внутренняя БД Loreport.
