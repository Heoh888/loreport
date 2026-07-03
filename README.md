# Loreport

> **Your repository knows more than your documentation.**

Open-source sidecar service that watches your repository and keeps **engineering lore** in sync with code.

Not GitBook. Not Confluence. Not another AI doc generator.  
**Grafana for engineering knowledge.**

---

## The Problem

Code changes constantly. Documentation dies.

After six months, nobody knows:

- why this service exists
- who uses this API
- which diagrams are stale
- which ADRs no longer match the code
- why this endpoint must not be removed

Code is the source of truth. Documentation is not.

## The Idea

**Lore** — accumulated knowledge, history, context, and reasons behind decisions.  
Every mature codebase develops its own lore. It is rarely written down explicitly.

**Loreport** — a living report of project knowledge. A platform that continuously analyzes the repository, builds a knowledge model, and surfaces it through an interactive UI.

## How It Fits Your Stack

```yaml
services:
  app:
    volumes: [./:/app]
  grafana:
    image: grafana/grafana
  postgres:
    image: postgres:16-alpine
  rabbitmq:
    image: rabbitmq:3-management-alpine
  loreport-api:
    image: loreport/loreport
    ports: ["3080:3080"]
    volumes: [./:/repo]
    environment:
      REPO_PATH: /repo
      DATABASE_URL: postgresql+asyncpg://loreport:${POSTGRES_PASSWORD}@postgres/loreport
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
  loreport-worker:
    image: loreport/loreport
    command: ["python", "-m", "loreport_server.worker.consumer"]
    volumes: [./:/repo]
    environment:
      REPO_PATH: /repo
      DATABASE_URL: postgresql+asyncpg://loreport:${POSTGRES_PASSWORD}@postgres/loreport
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      OPENROUTER_API_KEY: ${OPENROUTER_API_KEY}
```

Open `http://localhost:3080` — browse lore, check sync status, trigger updates.

## MVP Scope (v0.1)

- [ ] FastAPI sidecar + RabbitMQ worker + PostgreSQL
- [ ] Web UI: sync dashboard + docs browser (React)
- [ ] Git webhook + HEAD polling
- [ ] `init` / `update` agent runs (ported from [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki))
- [ ] Snapshot-based incremental updates (no empty sync loops)
- [ ] Single-repo, Docker Compose deploy

**Not in MVP:** multi-repo, RAG search, vulnerability scanning, AST graph, RBAC, auto-PR.

## Repository Structure (planned)

```
loreport/
├── backend/
│   ├── loreport_core/    # agent, git evidence, snapshots, prompts
│   └── loreport_server/  # FastAPI, worker, PostgreSQL, RabbitMQ
├── web/                  # React dashboard + docs browser
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── docs/
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11+, FastAPI |
| Database | PostgreSQL, SQLAlchemy, Alembic |
| Queue | RabbitMQ, aio-pika |
| Agent | deepagents, langchain (Python) |
| Frontend | React, Vite, shadcn |
| Deploy | Docker (api + worker) |

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/CONTEXT.md](./docs/CONTEXT.md) | Full project context (handoff for agents and contributors) |
| [docs/VISION.md](./docs/VISION.md) | Product vision and positioning |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Technical architecture |
| [docs/MVP.md](./docs/MVP.md) | MVP scope and sprint plan |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Version roadmap |
| [docs/OPENWIKI-ADAPTATION.md](./docs/OPENWIKI-ADAPTATION.md) | Porting agent logic from OpenWiki |

## Roadmap (summary)

| Version | Focus |
|---------|-------|
| **v0.1** | Living wiki + sync dashboard + Docker sidecar |
| **v0.3** | Dependency map + OpenAPI index |
| **v0.5** | Doc drift detection + auto-PR |
| **v1.0** | Knowledge graph explorer |

## License

MIT (planned). Agent logic adapted from [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki) (MIT).

## Status

**Pre-development.** Starter documentation only. Implementation not started.
