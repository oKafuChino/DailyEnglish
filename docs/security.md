# 安全设计

- 管理员身份仅匹配不可变的 Telegram 数字 ID。
- 邀请码使用安全随机数生成，数据库仅保存带 pepper 的 HMAC 摘要。
- 邀请码兑换通过行锁串行化，只允许成功一次。
- 注册、内容、回调与管理员命令使用独立限流桶。
- Token、邀请码、数据库 URL 和 API Key 会在完整日志输出后脱敏。
- Bot、Worker 和迁移容器以非 root 用户、只读文件系统运行。
- PostgreSQL 仅存在于 Compose 内部网络。

`.env` 权限应为 `0600`，不得提交到 Git。修改 `INVITE_CODE_PEPPER` 会使所有尚未兑换的邀请码失效。
