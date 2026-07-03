# Рабочие процессы

## Локальный запуск backend

В `backend/README.md` зафиксирован базовый цикл разработки:

```bash
cd backend
uv sync
uv run uvicorn loreport_server.api.main:app --reload --port 3080
```

Worker запускается отдельно:

```bash
uv run python -m loreport_server.worker.consumer
```

## Docker Compose workflow

В `docker/docker-compose.yml` описаны сервисы:

- `postgres`
- `rabbitmq`
- `loreport-api`
- `loreport-worker`

Ключевые параметры:

- `REPO_PATH` монтируется как `/repo`.
- `LOREPORT_DIR` по умолчанию равен `loreport`.
- `DATABASE_URL` и `RABBITMQ_URL` прокидываются через env.
- `POLL_INTERVAL_SEC` и `WEBHOOK_SECRET` задают поведение watcher.

## Sync workflow

### Trigger API

`POST /api/sync/trigger`:

- проверяет, что `REPO_PATH` существует;
- создаёт `SyncJob` в PostgreSQL;
- публикует сообщение в RabbitMQ;
- возвращает `job_id`.

### Status API

`GET /api/sync/status`:

- читает последний job из БД;
- пытается определить текущий git HEAD;
- нормализует состояния `pending` / `running` / `done` / `failed` в `idle` / `running` / `error` для UI.

### History API

`GET /api/sync/history` возвращает последние jobs с временем старта, завершения, флагом `changed`, моделью и ошибкой.

## Docs workflow

`GET /api/docs/tree`, `GET /api/docs/content`, `GET /api/docs/render` работают только с markdown внутри `REPO_PATH/loreport/`.

Правила:

- скрытые файлы и каталоги, начинающиеся с `.` или `_`, не попадают в дерево;
- доступны только `.md` файлы;
- HTML-рендер использует `markdown` с `tables` и `fenced_code`.

## Git webhook workflow

`POST /webhooks/git`:

- принимает JSON с полями `ref` и `after`;
- валидирует `X-Webhook-Secret`, если секрет задан;
- в текущем состоянии кодом только подтверждает принятие; debounce и публикация job пока отмечены TODO.

## Agent workflow

В `backend/loreport_core/agent/runner.py`:

1. Строится `RunContext` через `create_run_context()`.
2. Генерируется пользовательское сообщение `create_run_user_message()`.
3. Считается snapshot `before`.
4. Запускается `deepagents`-agent на `LocalShellBackend`.
5. Считается snapshot `after`.
6. Если контент изменился, пишется metadata.

## Что важно помнить

- `chat` существует в типах, но worker его не поддерживает.
- Путь `loreport/` используется в промптах и snapshot logic как основной output dir.
- Пустые обновления не должны загрязнять `.last-update.json`.
