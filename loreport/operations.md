# Операции

## Запуск и окружение

Фактические runtime-переменные, найденные в коде и документации:

- `REPO_PATH` — путь к смонтированному репозиторию, обычно `/repo`.
- `LOREPORT_DIR` — каталог lore внутри репозитория, обычно `loreport`.
- `DATABASE_URL` — строка подключения к PostgreSQL.
- `RABBITMQ_URL` — строка подключения к RabbitMQ.
- `POLL_INTERVAL_SEC` — интервал polling в секундах.
- `WEBHOOK_SECRET` — секрет для webhook.
- `LOREPORT_PROVIDER` / `LOREPORT_MODEL_ID` — выбор LLM provider/model.
- `STATIC_DIR` — директория собранного frontend static build.

## Docker Compose

`docker/docker-compose.yml` показывает текущую операционную схему:

- `postgres` хранит jobs, settings и будущие checkpoint'ы;
- `rabbitmq` обслуживает очереди sync;
- `loreport-api` запускает FastAPI на `:3080`;
- `loreport-worker` исполняет background jobs.

Заметки по конфигурации:

- сервисы ждут healthcheck зависимостей;
- volume с репозиторием монтируется read-write;
- секреты и пароли подаются через env, не через репозиторий.

## Dockerfile

`docker/Dockerfile` собирает runtime-образ на `python:3.12-slim`:

- ставит `git`;
- копирует `backend` и `web/dist`;
- выставляет `STATIC_DIR=/app/static`;
- стартует `uvicorn loreport_server.api.main:app`.

## Локальная разработка

Самый короткий цикл для backend:

1. `cd backend`
2. `uv sync`
3. `uv run uvicorn loreport_server.api.main:app --reload --port 3080`
4. в другом терминале — worker через `uv run python -m loreport_server.worker.consumer`

## Что проверять на окружении

- существует ли `REPO_PATH`;
- доступны ли PostgreSQL и RabbitMQ;
- корректно ли монтируется `loreport/`;
- не конфликтует ли `STATIC_DIR` со сборкой frontend;
- задан ли нужный provider key для выбранного LLM provider.
