#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BASE_URL="${BASE_URL:-http://127.0.0.1:${WEB_PORT:-8180}}"

cd -- "${INFRA_DIR}"
docker compose config --quiet
docker compose ps --status running
curl --fail --silent --show-error "${BASE_URL}/api/v1/health/live" >/dev/null
curl --fail --silent --show-error "${BASE_URL}/api/v1/health/ready" >/dev/null
docker compose exec -T api alembic current >/dev/null
printf 'release checks passed for %s\n' "${BASE_URL}"
