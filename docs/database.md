# 数据库

PostgreSQL 16 是唯一生产数据库。核心表包括：

- `users`：Telegram 身份、注册状态和推送设置。
- `invite_codes`：邀请码 HMAC 摘要、过期、兑换与撤销状态。
- `content_items`：单词、句子和内容元数据。
- `favorites`：用户收藏关系。
- `deliveries`：每日投递状态、尝试次数和 Telegram 消息 ID。
- `admin_audit_logs`：管理员敏感操作记录。

收藏关系和每日投递槽位使用唯一约束保证幂等。邀请码兑换和 Worker 任务领取使用 PostgreSQL 行锁处理并发。

所有结构变更必须同时更新 SQLAlchemy 模型和 Alembic 迁移。生成迁移后应审查 SQL，并执行：

```bash
alembic upgrade head --sql
alembic upgrade head
```

生产环境升级前必须运行 `scripts/backup.sh`。不要直接修改生产数据库表结构。
