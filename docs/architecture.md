# 系统架构

DailyEnglish 采用模块化单体结构，由三个容器组成：

- `bot`：aiogram Long Polling，处理注册、内容和收藏交互。
- `worker`：领取到期用户，执行每日单词与句子推送。
- `postgres`：保存用户、邀请码、内容、收藏、投递与审计记录。

Bot 和 Worker 共用 Service 与 Repository 层。Worker 使用短事务领取投递任务，Telegram 网络请求在事务外执行，再通过独立事务记录结果。每日投递通过数据库唯一约束避免重复创建。

首版不依赖 Redis、Celery 或公网 Webhook 端口。若未来运行多个 Bot 实例，需要将内存限流迁移到 Redis 等共享存储。
