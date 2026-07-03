#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PYTHON="/app/backend/.venv/bin/python"

echo "==> Building web"
cd "$ROOT/web"
corepack enable 2>/dev/null || true
pnpm install --frozen-lockfile
pnpm build

echo "==> Building Linux .venv at /app/backend (same path as runtime image)"
rm -rf "$ROOT/backend/.venv"

docker run --rm \
  -v "$ROOT/backend:/app/backend" \
  -w /app/backend \
  -e UV_HTTP_TIMEOUT=600 \
  python:3.12-slim \
  sh -c '
    set -e
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends curl ca-certificates git >/dev/null
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
    uv sync --frozen --no-dev
  '

if ! docker run --rm -v "$ROOT/backend:/app/backend" python:3.12-slim \
  test -x "$VENV_PYTHON"; then
  echo "ERROR: Linux venv was not created at $VENV_PYTHON" >&2
  exit 1
fi

echo "==> Docker image build"
cd "$ROOT/docker"
DOCKER_BUILDKIT=1 docker compose build "$@"
