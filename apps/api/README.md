# APT Hunter API

FastAPI API、数据库模型、Alembic 迁移和 Celery Worker 的工程基座。

## 本地运行

先从 `.env.example` 创建本地 `.env`，并替换其中所有 `change-me` 值。该文件已被 Git 忽略，禁止提交真实凭据。

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\uvicorn apt_hunter.main:app --reload
```

默认 API 地址为 `http://127.0.0.1:8000`，OpenAPI 为 `/docs`。
