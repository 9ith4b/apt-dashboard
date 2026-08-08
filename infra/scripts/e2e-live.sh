#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"
: "${APT_HUNTER_E2E_USERNAME:?set APT_HUNTER_E2E_USERNAME}"
: "${APT_HUNTER_E2E_PASSWORD:?set APT_HUNTER_E2E_PASSWORD}"

playwright_command="./node_modules/.bin/playwright test"
if [[ "${1:-}" == "--update-snapshots" ]]; then
  playwright_command="./node_modules/.bin/playwright test visual.spec.ts --update-snapshots"
fi

docker run --rm \
  --network host \
  --ipc host \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp/pw-home \
  --env APT_HUNTER_E2E_BASE_URL="${APT_HUNTER_E2E_BASE_URL:-http://127.0.0.1:8180}" \
  --env APT_HUNTER_E2E_USERNAME \
  --env APT_HUNTER_E2E_PASSWORD \
  --volume "${REPO_DIR}:/workspace" \
  --workdir /workspace/apps/web \
  mcr.microsoft.com/playwright:v1.62.1-noble \
  sh -lc "${playwright_command}"
