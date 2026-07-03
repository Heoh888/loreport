#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE="${LOREPORT_IMAGE:-${DOCKERHUB_USERNAME:?Set DOCKERHUB_USERNAME}/loreport:latest}"

echo "==> Building ${IMAGE}"
docker build -f "$ROOT/docker/Dockerfile" -t "$IMAGE" "$ROOT"

echo "==> Pushing ${IMAGE}"
docker push "$IMAGE"

echo "Done. Use in compose: LOREPORT_IMAGE=${IMAGE}"
