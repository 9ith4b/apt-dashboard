# 单机部署

1. 将 `.env.example` 复制为 `.env`，替换 PostgreSQL 与 MinIO 密码。
2. 将 `APT_HUNTER_IMAGE_TAG` 设置为 Git commit SHA 或发布版本；本地开发可保留 `dev`。
3. 在 `infra` 目录执行 `docker compose up -d --build`。
4. 打开 `http://localhost:8180`。
5. 执行 `./scripts/release-check.sh` 验证编排、迁移和健康端点。

PostgreSQL、Redis 和 MinIO API 不暴露到主机网络。MinIO 控制台与 Prometheus 默认仅绑定到 `127.0.0.1`，可通过 SSH 隧道查看：

```bash
ssh -L 9090:127.0.0.1:9090 apt-hunter@server.example.com
```

备份、恢复、监控、告警和发布操作见 [`../docs/operations-runbook.md`](../docs/operations-runbook.md)。
