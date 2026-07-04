# Architecture

## Overview

```
┌──────────────┐     ┌─────────────────────────────────────┐
│   web UI     │     │         loreport (1 container)       │
│   (React)    │◄───►│  FastAPI + in-process worker         │
└──────────────┘     └──────┬──────────────────┬───────────┘
                            │                  │
                            ▼                  ▼
                      SQLite (/data)    loreport_core agent
                            │                  │
                            └────────┬─────────┘
                                     ▼
                            /repo mount (target project)
                            loreport/*.md output
                            .last-update.json
```

**Deployment model:** one Docker container. API enqueues sync jobs into an in-process `asyncio.Queue`; the worker runs `process_job()` in the same Python process.

## Repository Layout

```
loreport/
├── backend/
│   ├── loreport_core/          # agent, git evidence, snapshots, prompts
│   └── loreport_server/        # FastAPI + worker
│       ├── api/routes/         # health, sync, docs, settings, webhooks
│       ├── queue/local.py      # in-process job queue
│       ├── worker/jobs.py      # process_job pipeline
│       └── db/                 # SQLAlchemy + SQLite
├── web/                        # React/Vite dashboard
└── docker/
    ├── Dockerfile
    └── docker-compose.yml
```

## Runtime Flow

### Sync trigger (UI)

```
1. POST /api/sync/trigger → SyncJob row in SQLite + enqueue payload
2. In-process worker dequeues:
   a. create_run_context() — git summary + last update metadata
   b. snapshot before/after — SHA-256 guard
   c. run_loreport_agent('init'|'update')
   d. If changed → write loreport/.last-update.json
   e. Update job record
3. UI polls GET /api/sync/status
```

### Snapshot guard

Hash `loreport/` excluding `.last-update.json`. If unchanged → `changed: false`, no metadata write.

## Storage

| Store | Location | Purpose |
|-------|----------|---------|
| Lore files | `{REPO_PATH}/loreport/` | Generated markdown (in target repo, not in Loreport VCS) |
| Update metadata | `{REPO_PATH}/loreport/.last-update.json` | Last successful sync |
| Job history | SQLite `sync_jobs` | Job status, errors, model |
| Secrets | Container env | API keys only |

## API

```
GET  /api/health
GET  /api/sync/status
POST /api/sync/trigger        { command, language? }
GET  /api/sync/history
GET  /api/docs/tree
GET  /api/docs/render?path=...
GET  /api/settings
POST /webhooks/git            (stub — not wired to jobs yet)
```

## Docker

Multi-stage: Node (web build) → uv (Python deps) → runtime (`python:3.12-slim`).

Published image: `alexhod/loreport:latest`.

```yaml
services:
  loreport:
    image: alexhod/loreport:latest
    ports: ["3080:3080"]
    volumes:
      - .:/repo:rw
      - loreport-data:/data
    environment:
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      LOREPORT_LANGUAGE: ru
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11+, FastAPI, uvicorn |
| Database | SQLite + SQLAlchemy async |
| Queue | in-process asyncio.Queue |
| Agent | deepagents + langchain |
| Frontend | React + Vite |
| Deploy | Docker single-container sidecar |

## Not implemented (v0.1 backlog)

- Git webhook → sync job
- HEAD polling scheduler
- PUT /api/settings
- Job history in UI

## Naming (from OpenWiki)

| OpenWiki | Loreport |
|----------|----------|
| `openwiki/` | `loreport/` |
| `OpenWikiCommand` | `LoreportCommand` |
| `runOpenWikiAgent` | `run_loreport_agent` |

Reference: [docs/OPENWIKI-ADAPTATION.md](./OPENWIKI-ADAPTATION.md)
