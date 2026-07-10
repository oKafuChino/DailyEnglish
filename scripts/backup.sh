#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
BACKUP_DIR="${DAILYENGLISH_BACKUP_DIR:-${PROJECT_DIR}/backups}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
cd "${PROJECT_DIR}"

if [[ ! -f .env ]]; then
  echo "缺少 ${PROJECT_DIR}/.env。" >&2
  exit 1
fi
if ! [[ "${RETENTION_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "BACKUP_RETENTION_DAYS 必须是非负整数。" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"
chmod 700 "${BACKUP_DIR}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="${BACKUP_DIR}/dailyenglish_${timestamp}.dump"
temporary="${target}.tmp"

cleanup() {
  rm -f -- "${temporary}"
}
trap cleanup EXIT

docker compose --env-file .env exec -T postgres sh -c \
  'pg_dump --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --format=custom --compress=6' \
  > "${temporary}"

docker compose --env-file .env exec -T postgres pg_restore --list \
  < "${temporary}" >/dev/null
mv -- "${temporary}" "${target}"
chmod 600 "${target}"

find "${BACKUP_DIR}" -maxdepth 1 -type f -name 'dailyenglish_*.dump' \
  -mtime "+${RETENTION_DAYS}" -delete

echo "备份完成：${target}"
