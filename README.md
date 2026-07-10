<div align="center">

# 📚 DailyEnglish Bot

**一个私密、轻量、可自部署的 Telegram 每日英语学习机器人**

每天推送一个英语单词和一句英语好句，支持内容收藏、随时复习和按需获取新内容。

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.x-26A5E4?logo=telegram&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Code style](https://img.shields.io/badge/code%20style-Ruff-D7FF64?logo=ruff&logoColor=black)

</div>

> [!NOTE]
> 项目目前处于早期开发阶段，应用骨架、数据库模型和初始迁移已经完成，机器人业务功能正在持续实现中。

## ✨ 项目愿景

DailyEnglish Bot 希望把英语积累变成一件简单且可以长期坚持的事情。用户无需安装额外应用，只需打开 Telegram，就能接收每日学习内容、收藏喜欢的表达，并在需要时快速复习。

机器人采用邀请码注册，只有管理员授权的用户才能使用，适合个人、小团队或学习社群自托管。

## 🚀 核心功能

- 📖 每天自动推送一个英语单词
- 💬 每天自动推送一句英语好句
- ⭐ 收藏单词和句子，随时分页查看
- 🔄 通过命令或按钮再获取一条内容
- 🕐 支持用户时区和自定义推送时间
- 🔐 一次性邀请码注册，防止机器人被滥用
- 👑 通过 Telegram 数字 ID 识别机器人管理员
- 🛠️ 管理员可生成、查看和撤销邀请码
- 🐳 支持 Docker Compose 一键部署到 VPS

## 📌 开发状态

- [x] Python 项目骨架与模块划分
- [x] 环境变量配置与运行入口
- [x] PostgreSQL 异步数据库层
- [x] 用户、邀请码、内容、收藏、投递和审计模型
- [x] Alembic 初始数据库迁移
- [x] Bot、Worker、PostgreSQL 容器编排
- [x] 数据库模型与配置测试
- [x] 管理员身份校验
- [x] 邀请码生成、撤销与一次性注册流程
- [x] 单词和句子内容服务与手动获取命令
- [x] 收藏、取消收藏与分页收藏列表
- [x] 每日定时推送 Worker 与失败重试
- [ ] 用户设置
- [x] 分级限流、日志脱敏与运行时安全校验
- [x] Docker 健康检查、日志轮转和 PostgreSQL 备份恢复
- [ ] 外部监控与告警

## 🏗️ 系统架构

```mermaid
flowchart LR
    User["👤 Telegram 用户"] --> API["Telegram Bot API"]
    API --> Bot["🤖 Bot 服务<br/>命令、注册、收藏"]
    Worker["⏰ 定时 Worker<br/>每日推送、失败重试"] --> API
    Bot --> DB[("🐘 PostgreSQL")]
    Worker --> DB
    Bot --> Content["📚 内容服务"]
    Worker --> Content
    Content --> Provider["本地内容库 / 词典 API / LLM"]
```

首版采用模块化单体架构，通过 Long Polling 连接 Telegram。VPS 无需为机器人开放 Webhook 端口，也不依赖 Redis 或 Celery。

## 🧰 技术栈

| 分类 | 技术 |
| --- | --- |
| 编程语言 | Python 3.12+ |
| Telegram 框架 | aiogram 3.x |
| 数据库 | PostgreSQL 16 |
| ORM | SQLAlchemy 2.x Async |
| 数据库迁移 | Alembic |
| 配置管理 | Pydantic Settings |
| 测试 | pytest、pytest-asyncio |
| 代码检查 | Ruff |
| 部署 | Docker、Docker Compose |

## 📁 项目结构

```text
DailyEnglish/
├── app/
│   ├── bot/                 # Router、Middleware、Filter、Keyboard 和状态机
│   ├── db/                  # SQLAlchemy 模型、会话和 Repository
│   ├── domain/              # 业务枚举和数据结构
│   ├── providers/           # 本地词库、词典 API 和 LLM Provider
│   ├── services/            # 注册、内容、收藏和投递业务逻辑
│   ├── workers/             # 每日推送和内容补充任务
│   ├── config.py            # 环境变量配置
│   └── main.py              # Bot 入口
├── migrations/              # Alembic 数据库迁移
├── tests/                   # 单元测试和集成测试
├── docs/                    # 架构、部署和安全文档
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

## ⚡ Ubuntu / Debian 一键部署

支持 Ubuntu 22.04 / 24.04 与 Debian 12。请先在 Telegram 中找到 [@BotFather](https://t.me/BotFather)，执行 `/newbot` 创建机器人并保存 Bot Token，同时准备好管理员的 Telegram 数字用户 ID。

登录服务器后执行：

```bash
curl -fsSL https://raw.githubusercontent.com/oKafuChino/DailyEnglish/main/scripts/install.sh | sudo bash
```

安装脚本会自动完成以下工作：安装 Docker 与 Git、拉取项目到 `/opt/dailyenglish`、生成数据库密码及邀请码密钥、创建 `.env`，最后构建并启动全部服务。执行过程中只会询问 Bot Token 和管理员 Telegram 数字 ID。

> [!IMPORTANT]
> 建议先打开安装脚本链接检查内容，再以 `sudo` 执行。脚本仅支持使用 `apt` 的 Ubuntu / Debian。

安装完成后查看状态和日志：

```bash
cd /opt/dailyenglish
sudo docker compose ps
sudo docker compose logs -f bot worker
```

更新到最新版本：

```bash
cd /opt/dailyenglish
sudo bash scripts/deploy.sh
```

部署脚本会检查 `.env` 与 Compose 配置，在数据库运行时先创建安全备份，然后拉取最新代码、重新构建镜像、执行数据库迁移，并等待 Bot 和 Worker 通过健康检查。若存在未提交的已追踪文件修改，脚本会停止更新以避免覆盖本地改动。

## 🧩 手动部署

### 1. 创建 Telegram Bot

在 Telegram 中找到 [@BotFather](https://t.me/BotFather)，执行 `/newbot` 创建机器人并保存 Bot Token。

你的 Telegram 数字用户 ID 将作为 `OWNER_TELEGRAM_ID`。请勿使用可修改的 Telegram 用户名作为管理员身份。

### 2. 配置环境变量

在 Ubuntu / Debian 服务器中克隆项目并复制环境变量模板：

```bash
git clone https://github.com/oKafuChino/DailyEnglish.git
cd DailyEnglish
cp .env.example .env
```

至少需要填写以下配置：

```env
BOT_TOKEN=你的-Telegram-Bot-Token
OWNER_TELEGRAM_ID=你的-Telegram-数字-ID
POSTGRES_PASSWORD=一个强数据库密码
DATABASE_URL=postgresql+asyncpg://dailyenglish:数据库密码@postgres:5432/dailyenglish
INVITE_CODE_PEPPER=一个足够长的随机密钥
```

> [!CAUTION]
> `.env` 包含 Bot Token 和数据库密码，已经被 `.gitignore` 排除。不要将其提交到 GitHub，也不要在日志或截图中公开。

### 3. 使用 Docker Compose 启动

```bash
docker compose up --build -d
```

查看服务状态与日志：

```bash
docker compose ps
docker compose logs -f bot worker
```

`migrate` 服务会先执行 `alembic upgrade head`，迁移成功后才启动 Bot 和 Worker。PostgreSQL 默认只在 Docker 内部网络中开放。

## 🐳 Docker 运维

查看容器状态、健康检查和最近日志：

```bash
cd /opt/dailyenglish
sudo docker compose ps
sudo docker compose logs --tail=200 bot worker postgres
```

重启应用服务：

```bash
sudo docker compose restart bot worker
```

停止或重新启动整套服务：

```bash
sudo docker compose down
sudo docker compose up -d
```

`docker compose down` 不会删除 PostgreSQL 数据卷。不要执行 `docker compose down -v`，除非确认需要永久删除数据库。

### 数据库备份

```bash
cd /opt/dailyenglish
sudo bash scripts/backup.sh
```

备份默认保存在 `/opt/dailyenglish/backups/`，使用 PostgreSQL Custom Format，并在写入完成前进行完整性校验。默认保留 14 天，可通过环境变量调整：

```bash
sudo BACKUP_RETENTION_DAYS=30 bash scripts/backup.sh
```

建议使用 root 的 Cron 每天执行：

```cron
30 3 * * * cd /opt/dailyenglish && /usr/bin/bash scripts/backup.sh >> /var/log/dailyenglish-backup.log 2>&1
```

### 数据库恢复

```bash
cd /opt/dailyenglish
sudo bash scripts/restore.sh backups/dailyenglish_YYYYMMDDTHHMMSSZ.dump
```

恢复脚本会先验证备份、再创建当前数据库的安全备份，然后暂停 Bot 和 Worker、原子恢复数据、执行最新迁移并重新启动服务。无人值守恢复可添加 `--yes`，但不建议在日常运维中使用。

### 容器安全

- Bot、Worker 和迁移容器使用固定的非 root 用户运行
- 应用文件系统为只读，仅 `/tmp` 使用受限内存文件系统
- 应用容器移除 Linux capabilities，并启用 `no-new-privileges`
- Docker 日志单文件最多 10 MB，保留 3 个轮转文件
- PostgreSQL 不映射宿主机端口，数据保存在命名卷 `dailyenglish_postgres_data`
- Bot 和 Worker 每 30 秒检查一次数据库连接状态

## 💻 Linux 本地开发

项目要求 Python 3.12 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

执行数据库迁移、测试和代码检查：

```bash
alembic upgrade head
pytest
ruff check .
ruff format --check .
```

## 🤖 规划中的机器人命令

| 命令 | 说明 |
| --- | --- |
| `/start` | 启动机器人或通过邀请链接注册 |
| `/register <邀请码>` | 使用一次性邀请码注册 |
| `/word` | 获取一个英语单词 |
| `/sentence` | 获取一句英语好句 |
| `/daily` | 获取今天的单词和句子 |
| `/saved` | 分页查看收藏内容 |
| `/settings` | 设置推送时间、时区和推送开关 |
| `/invite` | 管理员生成一次性邀请码 |
| `/invites` | 管理员查看邀请码状态 |
| `/revoke <邀请码ID>` | 管理员撤销尚未使用的邀请码 |

## 🗄️ 数据库设计

项目当前包含以下核心数据表：

- `users`：用户身份、注册状态、时区和推送设置
- `invite_codes`：邀请码摘要、有效期、兑换与撤销状态
- `content_items`：单词、句子、翻译、来源和内容状态
- `favorites`：用户收藏关系
- `deliveries`：每日及手动投递记录、状态和重试信息
- `admin_audit_logs`：管理员敏感操作审计记录

邀请码只保存经过密钥处理的摘要，不保存明文；收藏和每日投递均通过数据库唯一约束保证幂等性。

## 🔒 安全原则

- 管理员仅通过 Telegram 数字用户 ID 识别
- 一次性邀请码必须在数据库事务中原子兑换
- Bot Token、数据库密码和邀请码密钥只从环境变量读取
- PostgreSQL 不直接暴露到公网
- 所有用户命令和回调都需要注册状态校验
- 对内容请求、注册尝试和消息发送实施限流
- 日志不得记录 Token、邀请码明文或敏感用户内容
- 机器人仅在 Telegram 私聊中处理命令与收藏回调
- 启动时拒绝弱邀请码密钥、默认数据库密码和格式异常的 Bot Token

默认限流策略为：普通请求每分钟 30 次、内容请求每分钟 10 次、收藏回调每分钟 30 次、管理员命令每分钟 20 次、注册尝试每 5 分钟 5 次。所有阈值均可通过 `.env` 中的 `RATE_LIMIT_*` 配置调整；单机内存限流适用于默认的单 Bot 容器部署。

## 🧭 后续计划

下一阶段将优先实现管理员鉴权和一次性邀请码注册系统，随后开发内容获取、收藏和每日推送流程。完整功能会按“身份与权限 → 内容服务 → 用户交互 → 定时投递 → VPS 运维”的顺序推进。

---

<div align="center">

让英语学习成为每天都能坚持的小事。🌱

</div>
