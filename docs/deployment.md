# 部署

生产环境支持 Ubuntu 22.04/24.04 与 Debian 12，使用 Docker Compose v2。完整的一键安装、手动部署和升级步骤见项目根目录 `README.md`。

常用命令：

```bash
cd /opt/dailyenglish
sudo bash scripts/deploy.sh
sudo docker compose ps
sudo docker compose logs -f bot worker
```

部署脚本会检查工作区和 Compose 配置，在数据库运行时先备份，然后构建锁定依赖的镜像、执行迁移并等待健康检查。PostgreSQL 不映射宿主机端口。
