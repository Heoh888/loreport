# Loreport Backend

Python backend: `loreport_core` (agent library) + `loreport_server` (FastAPI + worker).

Agent logic adapted from [langchain-ai/openwiki](https://github.com/langchain-ai/openwiki) (MIT License).

## Local dev

```bash
cd backend
uv sync
uv run uvicorn loreport_server.api.main:app --reload --port 3080
```

Worker (separate terminal):

```bash
uv run python -m loreport_server.worker.consumer
```

## Docker

From repo root:

```bash
docker compose -f docker/docker-compose.yml up --build
```
