#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${HOME}/apt-hunter-backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
POSTGRES_USER="${POSTGRES_USER:-apt_hunter}"
POSTGRES_DB="${POSTGRES_DB:-apt_hunter}"

case "${BACKUP_DIR}" in
  ""|"/"|"${HOME}")
    echo "Refusing unsafe backup directory: ${BACKUP_DIR}" >&2
    exit 2
    ;;
esac
if ! [[ "${RETENTION_DAYS}" =~ ^[0-9]+$ ]] || (( RETENTION_DAYS < 1 )); then
  echo "RETENTION_DAYS must be a positive integer" >&2
  exit 2
fi

mkdir -p -- "${BACKUP_DIR}"
chmod 700 -- "${BACKUP_DIR}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
final_path="${BACKUP_DIR}/apt-hunter-${timestamp}.dump"
partial_path="${final_path}.partial"
trap 'rm -f -- "${partial_path}"' EXIT

cd -- "${INFRA_DIR}"
docker compose exec -T postgres pg_dump \
  --username "${POSTGRES_USER}" \
  --dbname "${POSTGRES_DB}" \
  --format custom \
  --no-owner \
  --no-privileges > "${partial_path}"

docker compose exec -T postgres pg_restore --list < "${partial_path}" >/dev/null
chmod 600 -- "${partial_path}"
mv -- "${partial_path}" "${final_path}"
sha256sum -- "${final_path}" > "${final_path}.sha256"
chmod 600 -- "${final_path}.sha256"
find "${BACKUP_DIR}" -maxdepth 1 -type f \
  \( -name 'apt-hunter-*.dump' -o -name 'apt-hunter-*.dump.sha256' \) \
  -mtime "+${RETENTION_DAYS}" -delete
trap - EXIT
printf '%s\n' "${final_path}"
