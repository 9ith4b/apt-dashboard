# 运维与发布手册

更新时间：2026-08-08

## 日常健康检查

```bash
cd /opt/apt-hunter/infra
./scripts/release-check.sh
docker compose ps
docker compose logs --since 30m api worker beat
```

Prometheus 默认只监听服务器 `127.0.0.1:9090`，可用 SSH 端口转发访问。已配置 API/依赖不可用、队列积压、失败作业和来源连续失败告警规则。部署环境尚未配置外部 Alertmanager，因此告警会在 Prometheus 中进入 firing 状态，但不会发送邮件或即时消息。

## 自动备份

`infra/scripts/backup.sh` 使用 PostgreSQL custom format 生成备份，先验证目录与 dump 清单，再原子改名并写 SHA-256。默认目录是 `~/apt-hunter-backups`，权限为 `0700`，文件权限为 `0600`，默认保留 14 天。

生产环境安装系统级定时器。服务仍以 `apt-hunter` 用户运行，只为该进程补充用户已有的 `docker` 组；这样不会依赖长期运行的用户 systemd 管理器是否刷新了组成员关系：

```bash
sudo cp infra/systemd/system/apt-hunter-backup.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now apt-hunter-backup.timer
```

查看状态：

```bash
systemctl list-timers apt-hunter-backup.timer
journalctl -u apt-hunter-backup.service
```

## 无损恢复演练

以下命令创建名称受限的临时数据库、恢复备份、读取迁移版本和核心表行数，然后自动删除临时库；不会连接或修改生产数据库：

```bash
cd /opt/apt-hunter/infra
./scripts/restore-verify.sh
```

## 生产恢复

生产恢复属于破坏性操作，必须先停止 Web/API/Worker/Beat、保存故障现场备份并由维护者明确确认目标 dump。优先恢复到新数据库并切换连接串，不要直接覆盖现有数据库。恢复后依次执行迁移、只读核对行数、启动服务和 `release-check.sh`。

## 发布与回滚

CI 对前后端格式、lint、类型、测试、OpenAPI、Compose、Shell、Prometheus 和镜像构建进行门禁。`v*` 标签会把 API/Web 镜像以发布标签和完整 Git SHA 发布到 GHCR，并附带 SBOM、provenance 与构建证明。

部署时设置：

```dotenv
APT_HUNTER_API_IMAGE=ghcr.io/<owner>/apt-hunter-api
APT_HUNTER_WEB_IMAGE=ghcr.io/<owner>/apt-hunter-web
APT_HUNTER_IMAGE_TAG=<full-git-sha-or-release>
```

然后执行 `docker compose pull`、数据库备份、`docker compose up -d` 和 `release-check.sh`。回滚时恢复上一个不可变镜像标签；只有发生不兼容数据库迁移时才执行经过审核的数据库恢复流程。

## 密钥与边界

- `.env`、初始管理员密码文件、社交平台 Token 与备份不得提交 Git。
- 当前可信内网 HTTP 部署必须在外层启用 HTTPS 后把 `APT_HUNTER_SESSION_SECURE_COOKIE` 改为 `true`。
- PostgreSQL、Redis、MinIO API 和 `/metrics` 不暴露到局域网；MinIO 控制台与 Prometheus 仅绑定 loopback。
