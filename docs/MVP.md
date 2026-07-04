# MVP Plan

## Goal

Ship a working sidecar in 4–6 weeks that proves the core loop:

> Mount repo → Loreport watches → lore updates → team browses in browser

## Scope

### In

- [x] Documentation and vision (this repo)
- [x] Backend (`backend/` — uv, `loreport_core`, `loreport_server`)
- [x] `web/` — React dashboard + docs browser (pnpm)
- [x] Agent ported from OpenWiki → Python `deepagents`
- [x] FastAPI standalone (SQLite + in-process worker)
- [ ] Git HEAD polling
- [ ] Git webhook endpoint
- [x] Docker Compose (single container)
- [x] Snapshot-based change detection
- [x] Single repository support

### Out (explicitly deferred)

See [Repository Integration Evolution](./ROADMAP.md#repository-integration-evolution) for the full git → PR path. MVP is phase **Observer** only.

- Multi-repo
- RAG / semantic search
- AST parsing / call graph
- Vulnerability scanning
- Doc drift detection
- User annotations (Lore → Code)
- RBAC / auth
- Auto git commit / PR creation
- SSE streaming (nice-to-have, use polling first)

## Definition of Done

1. `docker compose up` starts Loreport on `http://localhost:3080`
2. Dashboard shows: last sync time, git HEAD, job status, trigger button
3. Docs browser renders `loreport/*.md` from mounted repo
4. `POST /api/sync/trigger` enqueues init/update; worker completes job
5. Git push (or webhook) triggers automatic update within poll interval
6. Empty update (no content change) records `changed: false`, no metadata churn
7. Job history shows last 20 runs with status and duration

## Sprint 1 (Week 1–2): Core + Backend

### Day 1–2: Scaffold

```
loreport/
├── backend/
│   ├── pyproject.toml
│   ├── loreport_core/
│   └── loreport_server/
├── web/
└── docker/
    ├── Dockerfile
    └── docker-compose.yml
```

Tasks:
- Init backend with uv, ruff, mypy
- Port OpenWiki prompts + git/snapshot utils to `loreport_core` (Python)
- Rename `openwiki` → `loreport` in prompts and constants
- Add MIT attribution in `backend/loreport_core/README.md`
- Docker Compose: postgres + rabbitmq (dev infra)

### Day 3–4: API skeleton

- FastAPI app with `/api/health`
- PostgreSQL schema (Alembic): `jobs`, `settings`
- RabbitMQ publisher: `POST /api/sync/trigger` → publish job message
- `GET /api/sync/status` → latest job state from Postgres
- Worker stub: consume queue, update job status (no agent yet)

### Day 5–7: Agent integration

- Wire `run_loreport_agent('update')` in worker consumer
- Pre/post snapshot comparison
- Write `.last-update.json` only on change
- `GET /api/sync/history`
- Error handling, job failure recording, dead-letter on repeated failures

### Day 8–10: Watcher

- HEAD polling scheduler (in api process)
- `POST /webhooks/git` with secret validation
- Debounce: 30s coalescing window
- Settings: `pollIntervalSec`, `defaultBranch`

## Sprint 2 (Week 3–4): UI + Docker

### Day 11–13: Web UI

- Vite + React + shadcn setup in `web/`
- **Dashboard page:**
  - Current status badge (idle / running / error)
  - Last sync timestamp + git HEAD
  - "Sync now" button
  - Job history table
- **Docs browser:**
  - File tree from `GET /api/docs/tree`
  - Markdown viewer from `GET /api/docs/render`
- **Settings page:**
  - Provider + model selection (no secrets in UI, env-only for keys)

### Day 14–16: Docker

- Multi-stage Dockerfile (web build + Python runtime)
- docker-compose.yml: `loreport-api`, `loreport-worker`, `postgres`, `rabbitmq`
- Static web served by FastAPI
- README quick start: `docker compose up`

### Day 17–20: Polish + test

- Test on a real multi-service repo
- Fix agent path references (`loreport/` not `openwiki/`)
- AGENTS.md insertion in prompts
- Basic error states in UI
- `GET /api/docs/content` raw endpoint

## Tech Choices

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend language | Python 3.11+ | deepagents primary SDK; better for future indexers |
| API framework | FastAPI | Async, OpenAPI, fits worker/API split |
| ORM | SQLAlchemy 2.0 + asyncpg | Production-ready, multi-repo path |
| Migrations | Alembic | Standard for Postgres |
| Queue | RabbitMQ + aio-pika | Decouple API from long agent jobs; scale workers |
| Backend packages | uv | Fast, modern Python tooling |
| Frontend | React + Vite + shadcn (pnpm) | Fast to build, familiar |
| Markdown | markdown (Python) | Server-side render |
| Agent | deepagents (Python) | Port logic from OpenWiki TS reference |
| OpenWiki reference | TypeScript clone | Prompts and behavior only — not copied verbatim |

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REPO_PATH` | yes | `/repo` | Mounted repository path |
| `LOREPORT_DIR` | no | `loreport` | Output directory inside repo |
| `PORT` | no | `3080` | HTTP port (api) |
| `DATABASE_URL` | yes | — | PostgreSQL connection string |
| `RABBITMQ_URL` | yes | — | AMQP connection string |
| `POLL_INTERVAL_SEC` | no | `300` | HEAD polling interval |
| `WEBHOOK_SECRET` | no | — | Webhook auth secret |
| `OPENROUTER_API_KEY` | yes* | — | LLM provider key |
| `LOREPORT_PROVIDER` | no | `openrouter` | Provider name |
| `LOREPORT_MODEL_ID` | no | provider default | Model ID |
| `POSTGRES_PASSWORD` | yes | — | Postgres password (compose) |

*One provider API key required.

## Success Metrics (post-MVP)

- Time to first lore: < 15 min on medium repo (50k LOC)
- Update latency after push: < poll interval + agent runtime
- Empty update rate: correctly detected 100%
- UI load time: < 2s for docs tree

## Open Questions

1. **Output dir name:** `loreport/` or keep `openwiki/` for agent compatibility?
   - **Decision:** `loreport/` — own brand, update prompts accordingly
2. **Git write:** Should container commit changes or only write files?
   - **Decision MVP:** Write files only; host/CI commits
3. **Auth on UI:** Required for MVP?
   - **Decision:** No; add in v0.5
