#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_DIR}"

if [[ ! -f .env ]]; then
  echo "缺少 ${PROJECT_DIR}/.env，请先完成环境变量配置。" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "需要 Docker Engine 和 Docker Compose v2。" >&2
  exit 1
fi

chmod 600 .env
docker compose --env-file .env config --quiet

if [[ -d .git ]]; then
  if [[ -n "$(git status --porcelain)" ]]; then
    echo "检测到未提交或未追踪的文件，已停止自动更新。" >&2
    exit 1
  fi
  git pull --ff-only
fi

docker compose --env-file .env config --quiet

if docker compose --env-file .env ps --status running postgres --quiet | grep -q .; then
  bash scripts/backup.sh
fi

docker compose --env-file .env build --pull migrate
docker compose --env-file .env up -d --remove-orphans

echo "等待 Bot 和 Worker 通过健康检查..."
deadline=$((SECONDS + 180))
while (( SECONDS < deadline )); do
  bot_health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$(docker compose ps -q bot)" 2>/dev/null || true)"
  worker_health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "$(docker compose ps -q worker)" 2>/dev/null || true)"
  if [[ "${bot_health}" == "healthy" && "${worker_health}" == "healthy" ]]; then
    docker compose --env-file .env ps
    echo "部署完成。"
    exit 0
  fi
  sleep 3
done

docker compose --env-file .env ps
docker compose --env-file .env logs --tail=100 bot worker migrate >&2
echo "服务未在 180 秒内通过健康检查。" >&2
exit 1
