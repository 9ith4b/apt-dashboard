# APT Hunter

APT Hunter 是一个独立建设的 APT 威胁情报采集、分析、审核、狩猎与持续跟踪平台。

系统从 RSS、公开网页、X 和 Telegram 等来源收集安全信息，将多篇报道归并为去重攻击事件，并按照攻击钻石模型组织攻击者、能力、基础设施和受害目标。自动生成的重要结论必须保留原文证据并允许人工审核。

## 当前阶段

- 高保真产品原型：[`outputs/apt-hunter-prototype`](./outputs/apt-hunter-prototype)
- 产品与工程设计：[`outputs/apt-hunter-engineering-docs`](./outputs/apt-hunter-engineering-docs)
- 工程状态：M8 关注规则、通知、全局搜索与持久 Job 纵向切片已上线

当前已完成工程基座、RSS 数据源管理、定时采集、去重与 APT 相关性筛选；候选文章会自动抓取正文，按照攻击钻石模型提取对手、能力、基础设施和受害者，并沉淀带原文证据的 Observable 与 MITRE ATT&CK 技术。分析员可逐项保留、排除或补充实体，审核通过后系统会保留版本化修订并生成威胁事件。已确认事件中的组织名称会按别名归并为稳定档案，可按本月、本年、全部或自定义日期查看组织攻击事件、趋势和等长周期对比，并识别能力/恶意软件、基础设施、ATT&CK 技术和受害目标的新增或未再出现项。周期摘要保留支撑事件与 Evidence ID，可导出 JSON/CSV。相似事件只生成待审核候选，支持人工合并、驳回和可追溯撤销。Observable 可检索、查看事件上下文和本地富化，并在选择证据、用途、有效期、置信度及严重度后人工提升为 Indicator；Indicator 支持版本化撤销与恢复。分析员还可创建 Campaign，把已确认事件按阶段、置信度和证据说明加入可逆时间线。结构化关注规则可预览历史匹配或持久记录唯一命中，新确认事件会自动产生站内通知；顶部可聚合检索 Actor、Event、Observable 与 Report。采集和富化均使用持久 Job，可查看结果、非强制取消和重试链路。

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

详细需求、接口、数据模型和开发里程碑请从[工程文档索引](./outputs/apt-hunter-engineering-docs/README.md)开始阅读；当前实现状态见 [M8 状态说明](./docs/m8-status.md)，完整范围差距见[交付完成矩阵](./docs/completion-matrix.md)。

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
