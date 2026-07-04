# OpenWiki Adaptation Guide

Loreport ports agent **logic and prompts** from [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki) (MIT License) into **Python** using [deepagents](https://github.com/langchain-ai/deepagents).

Local reference clone (TypeScript): `/Users/aleksejhodakov/openwiki`

OpenWiki is TypeScript; Loreport backend is Python. **Do not copy files verbatim** — port behavior and prompts.

## Attribution

Include in `backend/loreport_core/README.md` and root `README.md`:

```
Agent logic adapted from langchain-ai/openwiki (MIT License)
https://github.com/langchain-ai/openwiki
```

## Files to Port (reference → Python)

| Source (OpenWiki TS) | Target (Loreport Python) | Notes |
|----------------------|--------------------------|-------|
| `src/agent/index.ts` | `loreport_core/agent/runner.py` | `run_loreport_agent()` |
| `src/agent/prompt.ts` | `loreport_core/prompts/` | Update paths and branding |
| `src/agent/utils.ts` | `loreport_core/git/` + `loreport_core/snapshot/` | Git evidence + snapshot |
| `src/agent/types.ts` | `loreport_core/types.py` | Extend with job types |
| `src/constants.ts` | `loreport_core/constants.py` | Rename dir constants |
| `src/env.ts` | `loreport_server/config.py` | Container env, not `~/.openwiki` |

## Files to NOT Port

| File | Reason |
|------|--------|
| `src/cli.tsx` | Replaced by web UI + FastAPI |
| `src/credentials.tsx` | Replaced by Settings page + env vars |
| `src/commands.ts` | Replaced by API routes + RabbitMQ jobs |

## Rename Map

Apply across ported modules:

| OpenWiki | Loreport |
|----------|----------|
| `OpenWiki` | `Loreport` |
| `openwiki` (dir) | `loreport` |
| `OPEN_WIKI_DIR` | `LOREPORT_DIR` |
| `OpenWikiCommand` | `LoreportCommand` |
| `runOpenWikiAgent` | `run_loreport_agent` |
| `createOpenWikiContentSnapshot` | `create_loreport_content_snapshot` |
| `createOpenWikiThreadId` | `create_loreport_thread_id` |
| `openwiki/quickstart.md` | `loreport/quickstart.md` |
| `~/.openwiki/.env` | Container env vars |
| `~/.openwiki/openwiki.sqlite` | PostgreSQL (LangGraph checkpointer) |

## Prompt Changes

In `loreport_core/prompts/`, update:

1. Agent identity: "You are Loreport..." not "You are OpenWiki..."
2. Output directory: `loreport/` not `openwiki/`
3. AGENTS.md section:

```markdown
## Loreport

This repository has engineering lore located in the /loreport directory.

Start here:
- [Loreport quickstart](loreport/quickstart.md)

Loreport includes repository overview, architecture notes, workflows, domain concepts, operations, integrations, testing guidance, and source maps.

When working in this repository, read the Loreport quickstart first, then follow its links to the relevant architecture, workflow, domain, operation, and testing notes.
```

4. Plan file: `loreport/_plan.md` (was `openwiki/_plan.md`)

## Python Dependencies

```toml
# backend/pyproject.toml (core)
dependencies = [
  "deepagents>=0.6",
  "langchain>=0.3",
  "langchain-openai",
  "langchain-anthropic",
  "langchain-openrouter",
  "langgraph-checkpoint-postgres",
]
```

Server adds: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `aiosqlite`, `markdown`.

Web adds its own deps via `web/package.json` (react, vite, shadcn).

## Behavior to Preserve

These OpenWiki patterns are critical — do not break them when porting:

### 1. Snapshot guard

```python
before = await create_loreport_content_snapshot(cwd)
# ... agent run ...
after = await create_loreport_content_snapshot(cwd)
if before != after:
    await write_last_update_metadata(command, cwd, model_id)
```

### 2. Git evidence

- `git status --short`
- `git rev-parse HEAD`
- Incremental log since `last_update.git_head` or `last_update.updated_at`
- `git diff --name-status HEAD`

### 3. Model fallback (OpenRouter)

Keep fallback model list for server-side errors (port `createModelRoute` logic).

### 4. Virtual filesystem paths

Agent uses `/README.md`, `/loreport/...` — not host absolute paths.

## Behavior to Change

### 1. Credential storage

OpenWiki: `~/.openwiki/.env` via interactive Ink UI.

Loreport: environment variables + Settings page (non-secret config in PostgreSQL).

```python
# loreport_server/config.py
def load_loreport_config() -> LoreportConfig:
    return LoreportConfig(
        repo_path=os.environ.get("REPO_PATH", "/repo"),
        loreport_dir=os.environ.get("LOREPORT_DIR", "loreport"),
        database_url=os.environ["DATABASE_URL"],
        rabbitmq_url=os.environ["RABBITMQ_URL"],
        provider=os.environ.get("LOREPORT_PROVIDER", "openrouter"),
        model_id=os.environ.get("LOREPORT_MODEL_ID"),
        poll_interval_sec=int(os.environ.get("POLL_INTERVAL_SEC", "300")),
        webhook_secret=os.environ.get("WEBHOOK_SECRET"),
    )
```

### 2. Checkpointer storage

OpenWiki: `~/.openwiki/openwiki.sqlite`

Loreport: PostgreSQL via `langgraph-checkpoint-postgres` (same cluster as job history).

### 3. Run lifecycle

OpenWiki: CLI calls agent directly, streams to Ink.

Loreport: API publishes to RabbitMQ → worker consumes → runs agent → updates PostgreSQL.

### 4. Auto-exit

OpenWiki: `shouldAutoExitStartupRun()` for TTY init/update.

Loreport: Not needed — worker daemon always running.

## New Types (extend `types.py`)

```python
LoreportCommand = Literal["init", "update", "chat"]
SyncJobStatus = Literal["pending", "running", "done", "failed"]

class SyncJob(BaseModel):
    id: str
    command: LoreportCommand
    status: SyncJobStatus
    started_at: datetime
    finished_at: datetime | None = None
    changed: bool | None = None
    snapshot_before: str | None = None
    snapshot_after: str | None = None
    git_head: str | None = None
    model: str | None = None
    error: str | None = None
```

## Testing Adaptation

1. Port agent core → run `init` against a test repo in isolation
2. Verify `loreport/` output (not `openwiki/`)
3. Verify snapshot skip on no-op update
4. Verify `.last-update.json` written only on change
5. Verify AGENTS.md section references `loreport/quickstart.md`
6. Verify worker acks RabbitMQ message only after job completes

## OpenWiki Features to Defer

| Feature | Loreport version |
|---------|------------------|
| Ink interactive chat | v0.2 (via web UI chat) |
| `--print` one-shot | v0.2 (CLI client) |
| `--dry-run` | v0.2 (dev mode) |
| LangSmith tracing | v0.2 (optional env) |
| GitHub Action template | v0.3 (optional, Docker preferred) |
