#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

assume_yes=false
if [[ "${1:-}" == "--yes" ]]; then
  assume_yes=true
  shift
fi
backup_file="${1:-}"

if [[ -z "${backup_file}" || ! -f "${backup_file}" ]]; then
  echo "用法：bash scripts/restore.sh [--yes] <备份文件.dump>" >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  echo "缺少 ${PROJECT_DIR}/.env。" >&2
  exit 1
fi

backup_file="$(cd -- "$(dirname -- "${backup_file}")" && pwd)/$(basename -- "${backup_file}")"
docker compose --env-file .env exec -T postgres pg_restore --list \
  < "${backup_file}" >/dev/null

if [[ "${assume_yes}" != true ]]; then
  read -r -p "恢复会覆盖当前数据库，输入 RESTORE 继续：" confirmation </dev/tty
  if [[ "${confirmation}" != "RESTORE" ]]; then
    echo "已取消恢复。"
    exit 0
  fi
fi

echo "先创建恢复前安全备份..."
bash scripts/backup.sh

services_stopped=false
restart_services() {
  if [[ "${services_stopped}" == true ]]; then
    docker compose --env-file .env up -d bot worker >/dev/null 2>&1 || true
  fi
}
trap restart_services EXIT

docker compose --env-file .env stop bot worker
services_stopped=true

docker compose --env-file .env exec -T postgres sh -c \
  'pg_restore --username="$POSTGRES_USER" --dbname="$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges --single-transaction' \
  < "${backup_file}"

docker compose --env-file .env run --rm migrate
docker compose --env-file .env up -d bot worker
services_stopped=false
trap - EXIT

echo "数据库恢复完成：${backup_file}"
