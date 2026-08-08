#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd -- "${INFRA_DIR}/.." && pwd)"

docker run --rm \
  --user "$(id -u):$(id -g)" \
  --volume "${REPO_DIR}:/workspace" \
  --workdir /workspace \
  node:24-alpine \
  sh -c "corepack pnpm audit --audit-level high"

cd -- "${INFRA_DIR}"
docker compose run --rm --no-deps \
  --user "$(id -u):$(id -g)" \
  --env XDG_CACHE_HOME=/tmp/security-cache \
  --volume "${REPO_DIR}/apps/api:/workspace" \
  --workdir /workspace \
  api \
  sh -c "python -m venv --system-site-packages /tmp/security-audit && \
    /tmp/security-audit/bin/python -m pip install --quiet --upgrade pip && \
    /tmp/security-audit/bin/python -m pip install --quiet -e '.[dev]' && \
    /tmp/security-audit/bin/bandit -q -r src && \
    /tmp/security-audit/bin/pip-audit --local"
