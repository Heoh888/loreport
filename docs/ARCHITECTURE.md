# Architecture

## Overview

```
┌──────────────┐     ┌──────────────┐     ┌─────────────────┐
│   web UI     │     │  loreport-api│     │ loreport-worker │
│   (React)    │◄───►│  (FastAPI)   │     │ (agent runner)  │
└──────────────┘     └──────┬───────┘     └────────┬────────┘
                            │                       │
              ┌─────────────┼─────────────┐         │
              ▼             ▼             ▼         ▼
        ┌──────────┐  ┌──────────┐  ┌──────────────────┐
        │PostgreSQL│  │ RabbitMQ │  │  loreport_core   │
        │ jobs,    │  │ sync jobs│  │  agent, git,     │
        │ settings │  │          │  │  snapshot        │
        └──────────┘  └──────────┘  └────────┬─────────┘
                                              │
                    ┌─────────────────────────┼─────────────────┐
                    ▼                         ▼                 ▼
              /repo (mount)              LLM API          git webhook
              loreport/ dir
              .last-update.json
```

**Deployment model:** one Docker image, two entrypoints (`api` / `worker`). API never runs agent jobs directly — it publishes to RabbitMQ.

## Repository Layout

```
loreport/
├── backend/
│   ├── pyproject.toml              # uv, workspace root
│   ├── loreport_core/              # Shared library, no HTTP
│   │   ├── agent/                  # DeepAgents runtime (ported from OpenWiki)
│   │   ├── git/                    # Git evidence collection
│   │   ├── snapshot/               # Content hash, drift detection
│   │   ├── prompts/                # System/user prompt builders
│   │   ├── constants.py            # Providers, models, paths
│   │   └── types.py
│   │
│   └── loreport_server/            # API + worker
│       ├── api/
│       │   ├── main.py             # FastAPI app
│       │   ├── routes/
│       │   │   ├── health.py
│       │   │   ├── sync.py         # trigger, status, history
│       │   │   ├── docs.py         # tree, content, render
│       │   │   ├── webhooks.py     # POST /webhooks/git
│       │   │   └── settings.py
│       │   └── deps.py
│       ├── worker/
│       │   ├── consumer.py         # RabbitMQ consumer
│       │   └── scheduler.py        # HEAD polling (runs in api or worker)
│       ├── db/
│       │   ├── models.py           # SQLAlchemy models
│       │   ├── session.py
│       │   └── migrations/         # Alembic
│       ├── queue/
│       │   ├── publisher.py        # aio-pika publish
│       │   └── messages.py         # job payload schema
│       ├── git/                    # Git provider adapter (evolution)
│       └── config.py               # env vars
│
├── web/                            # Frontend (pnpm)
│   ├── src/pages/
│   │   ├── Dashboard.tsx
│   │   ├── DocsBrowser.tsx
│   │   ├── DocViewer.tsx
│   │   └── Settings.tsx
│   └── src/api/                    # typed client for server API
│
└── docker/
    ├── Dockerfile
    └── docker-compose.yml
```

## Runtime Flow

### Sync Trigger (webhook or poll)

```
1. Webhook receives push event (or poller detects HEAD change)
2. API debounces (30s) and publishes to RabbitMQ: { command, repo_path, job_id }
3. Worker consumes message:
   a. create_run_context() — git summary + last update metadata
   b. create_content_snapshot() — SHA-256 before run
   c. run_loreport_agent('update') — DeepAgents with shell backend
   d. create_content_snapshot() — SHA-256 after run
   e. If changed → write .last-update.json
   f. Update job record in PostgreSQL
4. UI polls GET /api/sync/status
```

### Init (first run)

Same as update but `command: 'init'`, full git log (20 commits), creates `loreport/` directory structure.

### Snapshot Guard

Prevents empty update loops (critical for CI and polling):

- Hash `loreport/` directory excluding `.last-update.json`
- If before === after → job completes with `changed: false`, no metadata write
- Ported from OpenWiki `src/agent/utils.ts`

## Agent Backend

Conceptually ported from OpenWiki, implemented in Python:

- **deepagents** (`create_deep_agent`) with filesystem/shell backend
- Virtual paths: `/README.md`, `/loreport/quickstart.md`
- LangGraph checkpointer in PostgreSQL (same cluster, separate schema/table)
- Provider resolution: OpenRouter (default), Anthropic, OpenAI, Baseten, Fireworks
- Model fallback on OpenRouter server errors

## Message Queue (RabbitMQ)

| Setting | Value | Rationale |
|---------|-------|-----------|
| Exchange | `loreport.sync` (direct) | Single job type for MVP |
| Queue | `loreport.sync.jobs` | Durable |
| Prefetch | `1` per worker | Agent jobs are long-running |
| Ack | manual after job completes | Retry on worker crash |
| Dead letter | `loreport.sync.dlq` | Failed jobs after N retries |

**Library:** `aio-pika` (async publish in API, async consume in worker).

## Storage

| Store | Location | Purpose |
|-------|----------|---------|
| Lore files | `{REPO_PATH}/loreport/` | Generated markdown (git-tracked) |
| Update metadata | `{REPO_PATH}/loreport/.last-update.json` | Last successful sync head |
| Job history | PostgreSQL `jobs` table | Sync jobs, errors, timing |
| Settings | PostgreSQL `settings` table | Provider, model, poll interval |
| Agent checkpointer | PostgreSQL (LangGraph) | Agent conversation threads |
| Secrets | Container env vars | API keys, DB password (never in Postgres) |

## API

### Sync

```
GET  /api/sync/status
→ { state: 'idle'|'running'|'error', lastRun, head, snapshot, changed, error? }

POST /api/sync/trigger
→ { command: 'init'|'update', jobId }

GET  /api/sync/history?limit=20
→ [{ id, command, startedAt, finishedAt, changed, model, error? }]
```

### Docs

```
GET  /api/docs/tree
→ [{ path, name, children? }]

GET  /api/docs/content?path=architecture/overview.md
→ { path, content, updatedAt }

GET  /api/docs/render?path=...
→ { html }
```

### Webhooks

```
POST /webhooks/git
Headers: X-Webhook-Secret
Body: { ref, after, repository? }
→ publishes update job if ref matches default branch
```

### Settings

```
GET  /api/settings
→ { provider, modelId, pollIntervalSec }  // no secrets

PUT  /api/settings
→ updates non-secret settings
```

## Docker

### Dockerfile (multi-stage)

```
Stage 1: build web (pnpm + vite)
Stage 2: install backend (uv sync)
Stage 3: runtime (python:3.12-slim, copy backend + web static)
```

### Compose

```yaml
services:
  postgres:
    image: postgres:16-alpine
    volumes: [postgres-data:/var/lib/postgresql/data]
    environment:
      POSTGRES_DB: loreport
      POSTGRES_USER: loreport
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

  rabbitmq:
    image: rabbitmq:3-management-alpine
    volumes: [rabbitmq-data:/var/lib/rabbitmq]

  loreport-api:
    build: .
    command: ["uvicorn", "loreport_server.api.main:app", "--host", "0.0.0.0", "--port", "3080"]
    ports: ["3080:3080"]
    volumes:
      - ${REPO_PATH:-.}:/repo:rw
    environment:
      REPO_PATH: /repo
      LOREPORT_DIR: loreport
      DATABASE_URL: postgresql+asyncpg://loreport:${POSTGRES_PASSWORD}@postgres/loreport
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      POLL_INTERVAL_SEC: 300
      WEBHOOK_SECRET: ${WEBHOOK_SECRET}
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
    depends_on: [postgres, rabbitmq]
    restart: unless-stopped

  loreport-worker:
    build: .
    command: ["python", "-m", "loreport_server.worker.consumer"]
    volumes:
      - ${REPO_PATH:-.}:/repo:rw
    environment:
      REPO_PATH: /repo
      LOREPORT_DIR: loreport
      DATABASE_URL: postgresql+asyncpg://loreport:${POSTGRES_PASSWORD}@postgres/loreport
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
    depends_on: [postgres, rabbitmq]
    restart: unless-stopped
```

## Repository Integration (Evolution)

MVP uses a **volume mount + local git** only. The sidecar writes lore files; something else commits. Later versions add git platform APIs without changing the sidecar deployment model.

```
v0.1   REPO_PATH mount, git log/diff locally, write loreport/*.md
v0.2   GitHub Action template — CI commits/pushes after sync
v0.3   Provider config (token, branch, author) in settings
v0.4   PR context (diff, metadata) fed into agent prompt
v0.5   Auto branch + commit + PR via GitHub App / GitLab API
v0.6+  Per-repo git config in multi-repo mode
```

### Git Provider Adapter (planned)

```
backend/loreport_server/git/
├── local.py      # v0.1 — subprocess git in REPO_PATH
├── github.py     # v0.4+ — REST/GraphQL: PRs, commits, branches
├── gitlab.py     # v0.6+ — optional
└── types.py      # GitProvider, PullRequestContext, CommitRequest
```

| Capability | v0.1 | v0.3 | v0.5 |
|------------|------|------|------|
| Read HEAD / log / diff | local | local | local + API |
| Webhook: push | yes | yes | yes |
| Webhook: pull_request | — | — | yes |
| Write files | mount | mount | mount |
| git commit | — | CI template | Loreport |
| Open PR | — | CI template | Loreport |

**MVP constraint (intentional):** no git credentials in container — reduces scope and attack surface. `git/local.py` must expose an interface that `github.py` implements later without changing worker or agent code.

---

## Security (MVP)

- Webhook secret validation
- API keys via env only
- Agent prompt forbids reading `.env`, credentials
- Repo mount: agent writes only to `loreport/` inside mount
- No auth on MVP UI (add basic auth / SSO in v0.5)
- RabbitMQ credentials via env (not default guest in production)

## Extension Points

| Extension | Where |
|-----------|-------|
| New indexer (OpenAPI, AST) | `backend/loreport_core/indexers/` |
| New view (deps, drift) | `web/src/pages/` + `backend/loreport_server/api/routes/` |
| New agent task | `backend/loreport_core/prompts/` + queue message types |
| Multi-repo | PostgreSQL `repos` table + config |
| Scale workers | Add `loreport-worker` replicas (same queue) |

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend runtime | Python 3.11+ |
| API | FastAPI + uvicorn |
| ORM | SQLAlchemy 2.0 + asyncpg |
| Migrations | Alembic |
| Queue | RabbitMQ + aio-pika |
| Agent | deepagents + langchain (Python) |
| Frontend | React + Vite + shadcn (pnpm) |
| Markdown render | markdown (Python) |
| Package manager (backend) | uv |
| Deploy | Docker multi-stage |

## Naming Migration from OpenWiki

| OpenWiki | Loreport |
|----------|----------|
| `openwiki/` dir | `loreport/` dir |
| `.last-update.json` | `.last-update.json` (same) |
| `OpenWikiCommand` | `LoreportCommand` |
| `runOpenWikiAgent` | `run_loreport_agent` |
| AGENTS.md section text | Updated to reference `loreport/quickstart.md` |
