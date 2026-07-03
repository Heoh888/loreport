#!/usr/bin/env bash
# Download Linux arm64 wheels on the host for offline Docker build.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WHEELS_DIR="$ROOT/docker/wheels"
REQ_FILE="$ROOT/docker/requirements.txt"

mkdir -p "$WHEELS_DIR"
rm -f "$WHEELS_DIR"/*

PLATFORM="${UV_PYTHON_PLATFORM:-manylinux2014_aarch64}"
PYTHON_VERSION="${UV_PYTHON_VERSION:-3.12}"

echo "Vendoring wheels for platform=$PLATFORM python=$PYTHON_VERSION"

cd "$ROOT/backend"
uv lock
uv export --frozen --no-dev --no-emit-project --no-hashes -o "$REQ_FILE"

uv run --with pip python -m pip download \
  -r "$REQ_FILE" \
  --platform "$PLATFORM" \
  --python-version "$PYTHON_VERSION" \
  --only-binary=:all: \
  -d "$WHEELS_DIR"

echo "Done: $(ls -1 "$WHEELS_DIR" | wc -l | tr -d ' ') wheels in docker/wheels/"
