# 本地与单机部署

1. 将 `.env.example` 复制为 `.env`，替换两个密码。
2. 在 `infra` 目录执行 `docker compose up --build`。
3. 打开 `http://localhost:8180`。
4. API 存活检查：`http://localhost:8180/api/v1/health/live`。

数据库、Redis 和 MinIO API 不暴露到公网。MinIO 管理台默认仅绑定 `127.0.0.1:9101`。Web 端口、MinIO 管理台端口和 Worker 并发数均可通过 `.env` 调整。
