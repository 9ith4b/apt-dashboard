# APT Hunter API

FastAPI API、数据库模型、Alembic 迁移和 Celery Worker 的工程基座。

## 本地运行

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\uvicorn apt_hunter.main:app --reload
```

默认 API 地址为 `http://127.0.0.1:8000`，OpenAPI 为 `/docs`。
