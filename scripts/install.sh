#!/usr/bin/env bash
set -Eeuo pipefail

REPOSITORY_URL="https://github.com/oKafuChino/DailyEnglish.git"
INSTALL_DIR="${DAILYENGLISH_INSTALL_DIR:-/opt/dailyenglish}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 root 权限运行：curl ... | sudo bash"
  exit 1
fi

if [[ ! -r /etc/os-release ]]; then
  echo "无法识别操作系统，仅支持 Ubuntu 和 Debian。"
  exit 1
fi

# shellcheck disable=SC1091
source /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *)
    echo "当前系统为 ${PRETTY_NAME:-unknown}，仅支持 Ubuntu 和 Debian。"
    exit 1
    ;;
esac

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git openssl

if ! command -v docker >/dev/null 2>&1; then
  curl -fsSL https://get.docker.com | sh
fi

systemctl enable --now docker
docker compose version >/dev/null

if [[ -e "${INSTALL_DIR}" && ! -d "${INSTALL_DIR}/.git" ]]; then
  echo "安装目录 ${INSTALL_DIR} 已存在且不是 DailyEnglish Git 仓库。"
  exit 1
fi

if [[ -d "${INSTALL_DIR}/.git" ]]; then
  git -C "${INSTALL_DIR}" pull --ff-only
else
  git clone "${REPOSITORY_URL}" "${INSTALL_DIR}"
fi

if [[ ! -f "${INSTALL_DIR}/.env" ]]; then
  read -r -p "Telegram Bot Token: " BOT_TOKEN </dev/tty
  read -r -p "管理员 Telegram 数字 ID: " OWNER_TELEGRAM_ID </dev/tty

  if [[ -z "${BOT_TOKEN}" || ! "${OWNER_TELEGRAM_ID}" =~ ^[0-9]+$ ]]; then
    echo "Bot Token 不能为空，管理员 ID 必须是数字。"
    exit 1
  fi

  POSTGRES_PASSWORD="$(openssl rand -hex 24)"
  INVITE_CODE_PEPPER="$(openssl rand -hex 32)"

  cp "${INSTALL_DIR}/.env.example" "${INSTALL_DIR}/.env"
  sed -i \
    -e "s|^BOT_TOKEN=.*|BOT_TOKEN=${BOT_TOKEN}|" \
    -e "s|^OWNER_TELEGRAM_ID=.*|OWNER_TELEGRAM_ID=${OWNER_TELEGRAM_ID}|" \
    -e "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" \
    -e "s|^DATABASE_URL=.*|DATABASE_URL=postgresql+asyncpg://dailyenglish:${POSTGRES_PASSWORD}@postgres:5432/dailyenglish|" \
    -e "s|^INVITE_CODE_PEPPER=.*|INVITE_CODE_PEPPER=${INVITE_CODE_PEPPER}|" \
    "${INSTALL_DIR}/.env"
  chmod 600 "${INSTALL_DIR}/.env"
else
  echo "检测到已有 .env，将保留现有配置。"
fi

docker compose -f "${INSTALL_DIR}/docker-compose.yml" --env-file "${INSTALL_DIR}/.env" up --build -d

echo
echo "DailyEnglish 已安装到 ${INSTALL_DIR}"
echo "查看状态：cd ${INSTALL_DIR} && docker compose ps"
echo "查看日志：cd ${INSTALL_DIR} && docker compose logs -f bot worker"
