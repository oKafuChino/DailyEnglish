<div align="center">

# 📚 DailyEnglish Bot

**一个私密、轻量、可自部署的 Telegram 每日英语学习机器人**

每天推送一个英语单词和一句英语好句，支持内容收藏、随时复习和按需获取新内容。

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)
![aiogram](https://img.shields.io/badge/aiogram-3.x-26A5E4?logo=telegram&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Code style](https://img.shields.io/badge/code%20style-Ruff-D7FF64?logo=ruff&logoColor=black)
![Version](https://img.shields.io/badge/version-1.0.0-success)

</div>

> [!NOTE]
> 当前版本为 v1.0.0 正式版，已包含邀请注册、管理员工具、每日推送、收藏导出、难度筛选、限流安全、Docker 部署和备份恢复等核心能力。

## ✨ 项目愿景

DailyEnglish Bot 希望把英语积累变成一件简单且可以长期坚持的事情。用户无需安装额外应用，只需打开 Telegram，就能接收每日学习内容、收藏喜欢的表达，并在需要时快速复习。

机器人采用邀请码注册，只有管理员授权的用户才能使用，适合个人、小团队或学习社群自托管。

## 🚀 核心功能

- 📖 每天自动推送一个英语单词
- 💬 每天自动推送一句英语好句
- ⭐ 收藏单词和句子，随时分页查看
- 🧠 从收藏夹随机抽词复习，支持中文四选一和英文拼写双重考察
- 📤 支持将收藏单词导出为 Excel 表格
- 🔄 通过命令随时获取新的学习内容
- 🕐 用户可调整推送时区、时间和开关
- 🎚️ 用户可多选每日推送难度，未选择的难度不会出现在定时推送中
- 🔐 一次性邀请码注册，防止机器人被滥用
- 👑 通过 Telegram 数字 ID 识别机器人管理员
- 🛠️ 管理员可生成、查看和撤销邀请码
- 📊 管理员可查看运行统计，Worker 可在推送失败过多时告警
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
- [x] 12000 词高频通用分级词库（B1 3600 / B2 4800 / C1 3600）
- [x] 300 句原创双语句子库（B1 / B2 / C1 各 100 句）
- [x] 收藏、取消收藏与分页收藏列表
- [x] 收藏单词复习模式：中文四选一 + 英文拼写，自动冷却已掌握单词
- [x] 每日定时推送 Worker 与失败重试
- [x] 用户推送时间、时区与开关设置
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

如需允许管理员通过 Bot 触发远程更新，可在可信 VPS 上额外配置：

```env
ADMIN_UPDATE_COMMAND=/opt/dailyenglish/remote-update.sh
ADMIN_UPDATE_TIMEOUT_SECONDS=600
```

`ADMIN_UPDATE_COMMAND` 为空时 `/update` 不会执行任何系统命令。启用后它只能指向一个绝对路径的 `.sh` / `.bash` 脚本，程序会以 `bash <script>` 方式执行，不经过 shell 拼接。

如果 Bot 运行在 Docker 容器内，容器默认无法直接控制宿主机的 Docker Compose。要使用 `/update`，请自行准备安全 wrapper，例如只暴露固定部署脚本、使用受限 sudo 规则或宿主机侧 webhook；不要把 Docker socket 随意挂进 Bot 容器，也不要把脚本放在普通用户可写目录。

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

## 🤖 机器人命令

| 命令 | 说明 |
| --- | --- |
| `/start` | 启动机器人或通过邀请链接注册 |
| `/help` | 查看当前账号可用的指令 |
| `/register <邀请码>` | 使用一次性邀请码注册 |
| `/word` | 获取一个英语单词 |
| `/sentence` | 获取一句英语好句 |
| `/daily` | 获取今天的单词和句子 |
| `/saved` | 分页查看收藏内容 |
| `/review` | 从收藏夹随机抽取最多 10 个单词进行复习 |
| `/setting`、`/settings` | 设置推送时间、时区、推送开关和推送难度 |
| `/export_words` | 导出收藏单词 Excel 表格 |
| `/invite` | 管理员生成一次性邀请码 |
| `/invites` | 管理员查看邀请码状态 |
| `/revoke <邀请码ID>` | 管理员撤销尚未使用的邀请码 |
| `/stats` | 管理员查看用户、内容、收藏、投递和邀请码统计 |
| `/update` | 管理员执行已配置的远程更新命令，默认关闭 |

## 📚 单词内容库

项目内置 12000 个高频通用英语单词，随应用包一同部署，不依赖运行时网络请求。词库按项目学习难度规则划分为 B1 3600 个、B2 4800 个和 C1 3600 个；每条记录包含英文、中文释义、音标、词性、英文例句、难度和来源元数据。

原始词典数据来自 [ECDICT](https://github.com/skywind3000/ECDICT)，遵循 MIT License，许可文本见 `app/data/ECDICT_LICENSE`。B1、B2、C1 由本项目结合 ECDICT 词频排名与考试标签近似映射，并按约 30% / 40% / 30% 分层；构建时会优先保留高频、通用词，并过滤明显专名、缩写和专业领域词，仅用于内容分层，并非官方 CEFR 认证结果。

维护者可在 Ubuntu / Debian VPS 上一键下载 ECDICT 原始数据并重新生成本地词库：

```bash
bash scripts/update_word_library.sh
```

也可以使用已经下载好的原始 `ecdict.csv` 手动生成：

```bash
python scripts/build_word_library.py /path/to/ecdict.csv app/data/words.jsonl
python scripts/fill_word_examples.py --mode offline
```

`build_word_library.py` 负责重建词条、释义、音标和分级；`fill_word_examples.py` 负责为单词补充英文例句。默认 `offline` 模式不依赖网络，会生成项目原创模板例句；如需尝试在线词典例句，可使用 `--mode api`。不建议在 Bot 运行时实时依赖外部词典 API 批量取词，因为免费 API 往往存在限流、字段不稳定、中文释义不足和网络失败风险；更推荐定期离线重建 `words.jsonl`，再通过部署流程同步到数据库。

项目还内置 300 条原创双语句子，B1、B2、C1 各 100 条。句子标记为 `DailyEnglish Original`，可通过以下命令重复生成：

```bash
python scripts/build_sentence_library.py
```

Bot 和 Worker 每次启动时都会幂等同步包内内容库；同步会按内容指纹跳过未变化数据，并以流式分批方式读取词库，减少启动内存占用。更新已有 VPS 部署并重启容器后，程序会按内容哈希自动同步缺失内容，并将旧版包内 ECDICT 生僻词标记为不可推送；不会清空数据库或破坏用户收藏。

## 🗄️ 数据库设计

项目当前包含以下核心数据表：

- `users`：用户身份、注册状态、时区和推送设置
- `invite_codes`：邀请码摘要、有效期、兑换与撤销状态
- `content_items`：单词、句子、翻译、来源和内容状态
- `favorites`：用户收藏关系，以及收藏单词复习冷却、成功/失败次数
- `deliveries`：每日及手动投递记录、状态和重试信息
- `admin_audit_logs`：管理员敏感操作审计记录

邀请码只保存经过密钥处理的摘要，不保存明文；收藏和每日投递均通过数据库唯一约束保证幂等性。

收藏单词复习规则：`/review` 每轮最多随机抽取 10 个待复习收藏单词；每个单词先做英文到中文的四选一，再根据中文释义拼写英文。两关都通过的单词会暂时冷却 3 天，不会立即重复抽取；任一环节答错则继续保留在复习池中。当待复习池被抽空时，系统会自动开启新一轮复习池。

## 🔒 安全原则

- 管理员仅通过 Telegram 数字用户 ID 识别
- `/update` 远程更新默认关闭，只有显式配置 `ADMIN_UPDATE_COMMAND` 后才可用；只配置固定的 .sh 脚本绝对路径，不要指向可被普通用户修改的文件
- 一次性邀请码必须在数据库事务中原子兑换
- Bot Token、数据库密码和邀请码密钥只从环境变量读取
- PostgreSQL 不直接暴露到公网
- 所有用户命令和回调都需要注册状态校验
- 对内容请求、注册尝试和消息发送实施限流
- 日志不得记录 Token、邀请码明文或敏感用户内容
- 机器人仅在 Telegram 私聊中处理命令与收藏回调
- 启动时拒绝弱邀请码密钥、默认数据库密码和格式异常的 Bot Token

默认限流策略为：普通请求每分钟 30 次、内容请求每分钟 10 次、收藏回调每分钟 30 次、管理员命令每分钟 20 次、注册尝试每 5 分钟 5 次。所有阈值均可通过 `.env` 中的 `RATE_LIMIT_*` 配置调整；单机内存限流适用于默认的单 Bot 容器部署。

Worker 每轮推送失败数达到 `ALERT_FAILURE_THRESHOLD` 时，会向管理员 Telegram ID 发送告警；设置为 `0` 可关闭应用内告警。容器层健康状态仍由 Docker Compose healthcheck 负责。

## 🧪 测试与依赖

测试源码会提交到 GitHub，但 `.pytest_cache`、覆盖率报告等运行产物不会提交。GitHub Actions 会使用 PostgreSQL 16 执行代码检查、迁移、单元测试、数据库集成测试、Compose 配置校验和 Docker 镜像构建。

数据库集成测试具有破坏性，只允许数据库名以 `_test` 结尾或 `test_` 开头，并要求显式设置：

```bash
export TEST_DATABASE_URL=postgresql+asyncpg://user:password@localhost/dailyenglish_test
export TEST_DATABASE_RESET_CONFIRM=dailyenglish-test-database-reset
pytest tests/integration
```

保护条件会在建立连接和删除测试表之前执行。禁止将 `TEST_DATABASE_URL` 指向生产数据库。

生产与开发依赖通过 `requirements.lock` 固定版本。升级依赖时，应在独立分支更新锁文件并完整运行：

```bash
pip install -e ".[dev]"
pip freeze > requirements.lock
ruff check app migrations tests
pytest
```

## 🧭 后续计划

下一阶段将补充外部内容 Provider、异地备份、监控和告警。当前 `backups/` 位于 VPS 本机，生产环境应定期同步到另一台服务器或对象存储，避免单机磁盘故障同时丢失数据库与备份。

---

<div align="center">

让英语学习成为每天都能坚持的小事。🌱

</div>
