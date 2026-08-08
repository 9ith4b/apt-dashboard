#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${HOME}/apt-hunter-backups}"
POSTGRES_USER="${POSTGRES_USER:-apt_hunter}"
backup_path="${1:-}"

if [[ -z "${backup_path}" ]]; then
  backup_path="$(find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'apt-hunter-*.dump' -printf '%T@ %p\n' | sort -nr | head -n 1 | cut -d' ' -f2-)"
fi
if [[ -z "${backup_path}" || ! -f "${backup_path}" || "${backup_path}" != *.dump ]]; then
  echo "A readable .dump backup is required" >&2
  exit 2
fi
if [[ -f "${backup_path}.sha256" ]]; then
  sha256sum --check "${backup_path}.sha256"
fi

verify_db="apt_hunter_restore_verify_$(date -u +%Y%m%d%H%M%S)_$$"
if [[ ! "${verify_db}" =~ ^apt_hunter_restore_verify_[0-9_]+$ ]]; then
  echo "Unsafe verification database name" >&2
  exit 2
fi

cd -- "${INFRA_DIR}"
cleanup() {
  docker compose exec -T postgres dropdb \
    --username "${POSTGRES_USER}" \
    --if-exists "${verify_db}" >/dev/null
}
trap cleanup EXIT

docker compose exec -T postgres createdb --username "${POSTGRES_USER}" "${verify_db}"
docker compose exec -T postgres pg_restore \
  --username "${POSTGRES_USER}" \
  --dbname "${verify_db}" \
  --no-owner \
  --no-privileges < "${backup_path}"

docker compose exec -T postgres psql \
  --username "${POSTGRES_USER}" \
  --dbname "${verify_db}" \
  --set ON_ERROR_STOP=1 \
  --tuples-only \
  --command "SELECT 'alembic=' || version_num FROM alembic_version; SELECT 'sources=' || count(*) FROM sources; SELECT 'reports=' || count(*) FROM reports; SELECT 'users=' || count(*) FROM users;"

printf 'restore verification passed: %s -> %s\n' "${backup_path}" "${verify_db}"
