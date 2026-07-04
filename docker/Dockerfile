# syntax=docker/dockerfile:1
# Build from repo root: docker build -f docker/Dockerfile -t loreport/loreport:latest .

FROM node:22-bookworm-slim AS web
WORKDIR /src/web
RUN corepack enable
COPY web/package.json web/pnpm-lock.yaml web/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY web/ ./
RUN pnpm build

FROM python:3.12-slim AS python-deps
WORKDIR /app/backend
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.local/bin:$PATH"
COPY backend/ /app/backend/
RUN uv sync --frozen --no-dev

FROM python:3.12-slim AS runtime
WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=python-deps /app/backend /app/backend
COPY --from=web /src/web/dist /app/static
ENV PATH="/app/backend/.venv/bin:$PATH"
ENV STATIC_DIR=/app/static
ENV LOREPORT_DATA_DIR=/data
ENV REPO_PATH=/repo
WORKDIR /app/backend
EXPOSE 3080
CMD ["/app/backend/.venv/bin/python", "-m", "uvicorn", "loreport_server.api.main:app", "--host", "0.0.0.0", "--port", "3080"]
