# Vision

## One-liner

**Loreport** is an open-source sidecar that keeps engineering lore synchronized with your codebase.

## Slogan

> Your repository knows more than your documentation.

## Sub-slogans (for different contexts)

| Context | Copy |
|---------|------|
| Landing hero | Your repository knows more than your documentation. |
| Docker / infra | The knowledge port for your stack. |
| Developer | Understand your codebase, not just your code. |
| Long-term vision | The living knowledge graph of your repository. |

## The Problem

Software projects accumulate **implicit knowledge** that code alone cannot express:

- Architectural decisions and why they were made
- Deprecated approaches that must not return
- Endpoints that cannot be removed due to external clients
- Stale diagrams, ADRs, and README sections
- Cross-service dependencies that exist only in engineers' heads

Traditional documentation tools treat docs as **static artifacts**. They do not observe the repository. They do not detect drift. They do not evolve.

## The Solution

Loreport is a **continuous observer** — a container in your stack that:

1. Watches the repository (webhooks, polling, volume mounts)
2. Indexes structured signals (git, deps, OpenAPI, markdown, CI config)
3. Synthesizes **engineering lore** via AI where human context is missing
4. Presents a unified interactive view (dashboard + docs + future graph)
5. Allows the team to **add lore** that code will never contain

## What Loreport Is Not

- Not a wiki editor (Confluence replacement)
- Not a static site generator (MkDocs, Docusaurus)
- Not a one-shot AI doc CLI (though it adapts patterns from OpenWiki)
- Not a full SonarQube / Backstage replacement on day one

## What Loreport Is

- **Grafana for engineering knowledge** — a familiar infra pattern
- A **sidecar service** in docker-compose / k8s
- A **living model** of what the repository represents right now
- A **persistence layer** for knowledge that agents and humans can query

## Target Users

| User | Need |
|------|------|
| Small team (3–15) with microservices | Single view of multi-service knowledge |
| Self-hosted / on-prem teams | No cloud doc SaaS dependency |
| Agent-heavy workflows (Cursor, Claude Code) | API + structured lore for coding agents |
| Solo maintainer of growing OSS | Auto-maintained lore without manual wiki work |

## Not Target Users (initially)

- Solo dev with one small repo (Cursor chat is enough)
- Marketing documentation teams (use Mintlify, GitBook)
- Enterprises needing full Backstage catalog on day one

## Competitive Differentiation

```
Doc generators     →  one-shot or CI-batch markdown
Code intelligence  →  MCP tools for agents, no team UI
Catalog platforms  →  service registry, not repo-level lore
Loreport           →  sidecar + web UI + living sync + lore framing
```

## Core Concepts

### Lore

Accumulated engineering knowledge: history, context, reasons, relationships.  
Not a document. Not a wiki page. The **story of the codebase**.

### Port

The integration point in your infrastructure stack.  
Mount the repo, expose `:3080`, done.

### Knowledge Graph (long-term)

Deterministic edges from code structure + synthesized lore from AI + team annotations.  
Views (docs, deps, drift, security) are projections over the graph.

### Bidirectional Knowledge

- **Code → Lore**: automated analysis and synthesis
- **Lore → Code**: human and agent annotations persisted in the graph

## Success Criteria

1. A team can `docker compose up` and have lore within 30 minutes
2. Documentation updates happen without human intervention after git push
3. Developers check Loreport before touching unfamiliar modules
4. Coding agents query Loreport API instead of grepping blindly
5. Stale docs are **flagged**, not silently wrong

## Principles

1. **Ship narrow, sell broad** — MVP is living wiki + dashboard; vision is knowledge platform
2. **Deterministic first, LLM second** — graph edges from code; AI for synthesis only
3. **No empty sync loops** — snapshot-based change detection (from OpenWiki)
4. **Sidecar, not CLI** — infrastructure service pattern
5. **Open source, self-hosted** — MIT, no vendor lock-in
