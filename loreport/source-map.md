# Карта исходников

## Backend

### `backend/loreport_core`

- `agent/runner.py` — запуск `deepagents`-агента, snapshot guard, запись metadata.
- `git/evidence.py` — чтение last update, сбор git summary, формат evidence.
- `constants.py` — `LOREPORT_DIR`, provider/model resolution, update metadata file name.
- `prompts.py` — system/user prompts для agent-run.
- `snapshot/` — snapshot logic для каталога lore.
- `types.py` — типы команд и payload'ов.

### `backend/loreport_server`

- `api/main.py` — FastAPI app, lifespan, static serving.
- `api/routes/health.py` — health endpoint.
- `api/routes/sync.py` — trigger/status/history/snapshot.
- `api/routes/docs.py` — docs tree/content/render.
- `api/routes/webhooks.py` — git webhook endpoint.
- `api/routes/settings.py` — settings API.
- `config.py` — env-based settings.
- `db/models.py` — SQLAlchemy модели job/settings.
- `db/session.py` — session init и dependency.
- `queue/publisher.py` — публикация sync jobs в RabbitMQ.
- `worker/consumer.py` — consumer, который исполняет jobs.

## Frontend

- `web/package.json` — React/Vite scaffold и scripts.
- `web/src/` — UI source, пока почти пустой scaffold.

## Docker и инфраструктура

- `docker/docker-compose.yml` — сервисы, env wiring, healthchecks, volumes.
- `docker/Dockerfile` — runtime image.
- `scripts/docker-build.sh` — build helper.
- `scripts/vendor-python-wheels.sh` — wheel vendoring helper.

## Документы верхнего уровня

- `README.md` — позиционирование и предполагаемая структура.
- `docs/ARCHITECTURE.md` — подробная архитектурная карта.
- `docs/CONTEXT.md` — исторический и продуктовый контекст.
- `docs/MVP.md` — scope, DoD и env vars.
- `docs/VISION.md` — vision statement.
- `docs/ROADMAP.md` — эволюция версий.
- `docs/OPENWIKI-ADAPTATION.md` — правила адаптации OpenWiki.
