# Аудит репозитория Loreport

Дата: 2026-07-05

---

## Сделано

### Infra / docs
- [x] README, ARCHITECTURE — standalone, без RabbitMQ/PostgreSQL
- [x] `.dockerignore`, `.gitignore` (`loreport/` — runtime output)
- [x] Удалены: `scripts/`, distributed compose, orphaned tests

### Backend
- [x] RabbitMQ/distributed mode удалён — in-process worker (`queue/local.py`)
- [x] `alembic`, модель `Setting`, `POLL_INTERVAL_SEC`
- [x] Path traversal fix в `docs.py`
- [x] Мёртвый код: `chat`, unused git helpers, unused constants

### Frontend
- [x] Mermaid rendering + doc link routing (`/docs/...`)
- [x] `Cache-Control: no-cache` для index.html

### Git
- [x] `loreport/` (generated docs) убран из VCS

---

## Осталось

| Задача | Приоритет |
|--------|-----------|
| Webhook → sync job | Medium |
| Job history UI | Low |
| PUT /api/settings | Low |
| LICENSE | Low |

---

## Архитектура (факт)

```
1 container = FastAPI + asyncio worker + SQLite
REPO_PATH/loreport/ = output в анализируемом репо
```
