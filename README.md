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

Standalone sidecar — one container, SQLite, in-process worker:

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

volumes:
  loreport-data:
```

Open `http://localhost:3080` — browse lore, check sync status, trigger init/update.

**Local development** (build from source):

```bash
docker compose -f docker/docker-compose.yml up --build
```

Set `REPO_PATH=..` in `.env` to analyze this repo itself.

## MVP Scope (v0.1)

- [x] FastAPI sidecar (standalone: SQLite + in-process worker)
- [x] Web UI: sync dashboard + docs browser (React)
- [x] `init` / `update` agent runs (ported from [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki))
- [x] Snapshot-based incremental updates (no empty sync loops)
- [x] Language selection for generated docs
- [x] Docker image on Docker Hub (`alexhod/loreport`)
- [ ] Git webhook → sync job
- [ ] HEAD polling scheduler

**Not in MVP:** multi-repo, RAG search, vulnerability scanning, AST graph, RBAC, auto-PR.

## Repository Structure

```
loreport/
├── backend/
│   ├── loreport_core/    # agent, git evidence, snapshots, prompts
│   └── loreport_server/  # FastAPI + worker
├── web/                  # React dashboard + docs browser
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
└── docs/
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy |
| Database | SQLite (standalone) |
| Agent | deepagents, langchain (Python) |
| Frontend | React, Vite |
| Deploy | Docker single-container sidecar |

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/CONTEXT.md](./docs/CONTEXT.md) | Full project context (handoff for agents and contributors) |
| [docs/VISION.md](./docs/VISION.md) | Product vision and positioning |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | Technical architecture |
| [docs/MVP.md](./docs/MVP.md) | MVP scope and sprint plan |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | Version roadmap |
| [docs/OPENWIKI-ADAPTATION.md](./docs/OPENWIKI-ADAPTATION.md) | Porting agent logic from OpenWiki |
| [docs/AUDIT.md](./docs/AUDIT.md) | Repo audit and cleanup backlog |

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

**v0.1 MVP** — standalone sidecar, agent init/update, web UI, Docker Hub image. Webhook and polling not yet implemented.
