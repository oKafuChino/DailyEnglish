# DailyEnglish Bot v1.0.0 发布说明

DailyEnglish Bot v1.0.0 是面向 Ubuntu / Debian VPS 自托管部署的正式版本。

## 核心能力

- 邀请码注册，仅授权用户可使用机器人。
- Telegram 数字 ID 管理员识别。
- 管理员生成、查看、撤销一次性邀请码。
- 每日自动推送单词和句子。
- `/word`、`/sentence`、`/daily` 手动获取内容。
- 用户可多选推送难度，未选择难度不会推送。
- 收藏内容分页查看。
- 收藏单词导出 Excel。
- `/setting` 配置推送时间、时区、开关和难度。
- `/stats` 管理员统计。
- 可选 `/update` 管理员远程更新，默认关闭，仅允许固定脚本路径。
- 内置 12000 个高频通用英语单词和 300 条双语句子。
- Docker Compose 部署、数据库迁移、备份和恢复脚本。
- 限流、日志脱敏、弱配置启动校验和容器安全加固。

## 正式版前安全处理

- `/update` 不再执行任意 shell 字符串，只允许配置绝对路径 `.sh` / `.bash` 脚本。
- Bot 容器默认不挂载 Docker socket。
- PostgreSQL 不映射公网端口。
- Bot / Worker / migrate 容器使用非 root 用户运行。
- 应用容器启用只读文件系统、`no-new-privileges` 和 `cap_drop: ALL`。
- `.env`、Bot Token、数据库密码、邀请码密钥、更新脚本路径会被日志脱敏。
- 测试数据库重置具备强保护条件，避免误删生产库。

## 词库与内存优化

- 词库从 50000 个长尾词精简为 12000 个高频通用词。
- 构建时过滤明显专业领域词、人名、地名、缩写和异常词形。
- 词库读取改为流式分批同步，降低 VPS 启动内存占用。
- 更新部署后，旧版包内 ECDICT 生僻词会标记为不可推送，不会删除用户收藏。

## 发布前验证

```text
pytest
ruff check
ruff format --check
compileall
```

以上检查均应通过后再部署生产 VPS。
