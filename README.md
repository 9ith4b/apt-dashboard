# APT Hunter

APT Hunter 是一个独立建设的 APT 威胁情报采集、分析、审核、狩猎与持续跟踪平台。

系统从 RSS、公开网页、X 和 Telegram 等来源收集安全信息，将多篇报道归并为去重攻击事件，并按照攻击钻石模型组织攻击者、能力、基础设施和受害目标。自动生成的重要结论必须保留原文证据并允许人工审核。

## 当前阶段

- 高保真产品原型：[`outputs/apt-hunter-prototype`](./outputs/apt-hunter-prototype)
- 产品与工程设计：[`outputs/apt-hunter-engineering-docs`](./outputs/apt-hunter-engineering-docs)
- 工程状态：M3 字段级复核与威胁事件沉淀纵向切片已上线

当前已完成工程基座、RSS 数据源管理、定时采集、去重与 APT 相关性筛选；候选文章会自动抓取正文，按照攻击钻石模型提取对手、能力、基础设施和受害者。分析员可逐项保留、排除或补充实体，审核通过后系统会保留版本化修订并生成威胁事件。

部署环境访问地址：`http://server.example.com:8180`。

## 技术基线

- Web：React、TypeScript、Vite、Tailwind CSS、shadcn/ui
- API：FastAPI、Pydantic、SQLAlchemy、Alembic
- 数据与任务：PostgreSQL、Redis、Celery、MinIO
- 部署：Docker Compose

## 目录规划

```text
apps/web/       前端应用
apps/api/       FastAPI 应用与 Worker
infra/          本地开发和部署编排
outputs/        原型与工程设计文档
```

详细需求、接口、数据模型和开发里程碑请从[工程文档索引](./outputs/apt-hunter-engineering-docs/README.md)开始阅读；当前实现状态见 [M3 状态说明](./docs/m3-status.md)。

## 开发命令

### Web

```powershell
pnpm install
pnpm dev:web
pnpm lint:web
pnpm typecheck:web
pnpm test:web
pnpm build:web
```

### API

```powershell
cd apps/api
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\ruff check .
.\.venv\Scripts\pytest
.\.venv\Scripts\uvicorn apt_hunter.main:app --reload
```

### 完整环境

```powershell
Copy-Item infra/.env.example infra/.env
cd infra
docker compose up --build
```

打开 `http://localhost:8180`。本机仅开发 Web 时使用 `http://localhost:5173`。
