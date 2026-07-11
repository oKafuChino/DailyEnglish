# 运维

创建与恢复数据库备份：

```bash
sudo bash scripts/backup.sh
sudo bash scripts/restore.sh backups/dailyenglish_YYYYMMDDTHHMMSSZ.dump
```

备份默认保留 14 天。恢复前会再次创建安全备份，并在恢复期间停止 Bot 和 Worker。备份必须定期同步到异地服务器或对象存储。

Docker 健康检查只能确认进程和数据库连接状态。生产环境仍应监控容器重启次数、磁盘空间、备份新鲜度和 Telegram 投递失败率。
