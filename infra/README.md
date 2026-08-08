# 本地与单机部署

1. 将 `.env.example` 复制为 `.env`，替换两个密码。
2. 在 `infra` 目录执行 `docker compose up --build`。
3. 打开 `http://localhost:8080`。
4. API 存活检查：`http://localhost:8080/api/v1/health/live`。

数据库、Redis 和 MinIO API 不暴露到公网。MinIO 管理台仅绑定 `127.0.0.1:9001`。
