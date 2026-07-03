# Roadmap

Ship narrow, sell broad. Each version adds a **layer of truth** without breaking the sidecar model.

## Layer Model

| Layer | Sources | Capability |
|-------|---------|------------|
| **L0** | Git, files, markdown, ADR | Living wiki + sync dashboard |
| **L1** | package.json, OpenAPI, Docker, CI | Dependency + API map |
| **L2** | AST, imports, routes | Call graph, dead code candidates |
| **L3** | L0–L2 combined | Doc drift detection |
| **L4** | L0–L3 + external feeds | Security, debt, impact analysis |

---

## North Star: Repository as Source of Truth

Loreport is not a hosted wiki. The **canonical lore lives in the git repository** (`loreport/`, ADRs, architecture docs). The sidecar observes code, updates lore in-repo, and eventually participates in the same review workflow as human contributors.

```
Code change (commit / merge)
       │
       ▼
Loreport detects change
       │
       ▼
Agent updates lore in repository
       │
       ▼
Change delivered via git (commit → PR → merge)   ← full vision
       │
       ▼
Team reviews lore like any other code change
```

MVP intentionally stops before git write credentials and PR automation. Architecture must not block this path.

### Repository Integration Evolution

| Phase | Version | What Loreport reads | What Loreport writes | Delivery |
|-------|---------|---------------------|----------------------|----------|
| **Observer** | v0.1 | Local git: HEAD, log since last sync, diff | Files in mounted repo (`loreport/`) | Host or CI commits |
| **CI bridge** | v0.2–0.3 | Same + CI workflow context | Same; optional Action template | GitHub Action push/PR |
| **PR-aware** | v0.4–0.5 | PR diff, review comments via provider API | Branch + commit | Opens PR for review |
| **Maintainer** | v0.6+ | Multi-repo, drift signals | Targeted updates per repo | Auto-PR on drift or schedule |

**Principles (all versions):**

- Lore files are git-tracked artifacts in the target repo, not Loreport-internal storage
- Git write scope: `loreport/` and explicitly declared doc paths only — never arbitrary source edits
- PR-based delivery is the default for teams; direct push is opt-in (solo dev, trusted bot)
- Loreport integrates with GitHub/GitLab — it does not replace code review or become a git host

**Extension point:** `backend/loreport_server/git/` — provider adapter (`local` → `github` → `gitlab`) shared by webhook handler, poller, and future PR publisher.

---

## v0.1 — Living Lore Sidecar (MVP)

**Theme:** Prove the sidecar loop works.

- Sidecar: FastAPI + RabbitMQ worker + PostgreSQL
- Web UI: sync dashboard + docs browser
- Git webhook + HEAD polling
- Agent init/update (ported from OpenWiki → Python deepagents)
- Snapshot-based incremental sync
- Docker Compose deploy (api, worker, postgres, rabbitmq)
- Single repository

**Outputs:** `loreport/*.md`, `.last-update.json`, job history in PostgreSQL

---

## v0.2 — Agent API + Polish

**Theme:** Make lore queryable by coding agents.

- REST API for lore content (`/api/context`)
- SSE streaming for sync progress
- Basic auth on UI
- `loreport/quickstart.md` auto-generation template
- CLI thin client (`loreport trigger`, `loreport status`)
- Improved error diagnostics in dashboard
- GitHub Action template: commit `loreport/` changes after sync (optional CI bridge)

---

## v0.3 — Structured Index (L1)

**Theme:** Deterministic facts, not just LLM prose.

- Indexer: `package.json`, `go.mod`, `requirements.txt` → dependency list
- Indexer: OpenAPI / GraphQL schema → API map view
- Indexer: `Dockerfile`, `docker-compose.yml` → container map
- Indexer: `.github/workflows/` → CI/CD overview
- New UI page: **Dependencies**
- New UI page: **API Map**
- Git provider config: token, default branch, commit author (prep for v0.5 PR flow)

---

## v0.4 — Team Lore (bidirectional)

**Theme:** Humans add what code cannot say.

- UI annotations: pin notes to files, modules, endpoints
- "Do not remove" / "Client X depends on this" flags
- Annotation storage in PostgreSQL + optional export to `loreport/annotations/`
- Agent prompt includes team annotations in context
- Read PR context: diff, title, description — enrich update jobs (webhook on PR sync optional)

---

## v0.5 — Drift Detection (L3)

**Theme:** Flag lies, don't just generate text.

- Compare indexed API routes vs markdown API docs
- Compare dependency list vs architecture docs
- Compare ADR claims vs current code structure
- Dashboard widget: **Stale Lore Alerts**
- Indexer: ADR files (`docs/adr/`, `adr/`)
- **Auto-PR:** branch → commit lore changes → open PR when drift detected or sync produces diff
- Dashboard: pending lore PRs, merge status

---

## v0.6 — Multi-Repo

**Theme:** One Loreport for the whole stack.

- Register multiple repos (microservices)
- Per-repo sync jobs and status
- Cross-repo dependency view (shared packages, API consumers)
- Compose generator: add Loreport block to existing stack

---

## v1.0 — Knowledge Graph (L2 + L4)

**Theme:** Full vision — graph explorer.

- AST indexer (tree-sitter): imports, call edges
- Graph storage (PostgreSQL JSONB or optional Neo4j)
- UI: interactive graph explorer
- Views: dead code candidates, orphan modules, ownership
- Impact analysis: "what breaks if I change X?"
- Optional: vulnerability feed integration (OSV, Dependabot API)

---

## v1.x — Platform

- RAG search over lore + code
- Plugin system for custom indexers and views
- SSO (OIDC)
- Kubernetes Helm chart
- Managed cloud offering (optional, separate from OSS)

---

## What We Will Not Build

- Full Backstage replacement (service catalog, scaffolder)
- Full SonarQube replacement (deep static analysis, quality gates)
- Git hosting / code review platform
- General-purpose agent framework

Loreport **integrates with** these tools, not replaces them.

---

## Positioning by Version

| Version | Public message |
|---------|----------------|
| v0.1 | Grafana for engineering knowledge — start with living wiki |
| v0.3 | See your repo's dependencies, APIs, and containers — automatically |
| v0.5 | Know when your docs are lying — Loreport opens PRs to fix them |
| v1.0 | The knowledge graph of your codebase |
