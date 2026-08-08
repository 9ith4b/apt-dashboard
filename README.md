# APT Hunter

APT Hunter 是一个独立建设的 APT 威胁情报采集、分析、审核、狩猎与持续跟踪平台。

系统从 RSS、公开网页、X 和 Telegram 等来源收集安全信息，将多篇报道归并为去重攻击事件，并按照攻击钻石模型组织攻击者、能力、基础设施和受害目标。自动生成的重要结论必须保留原文证据并允许人工审核。

## 当前阶段

- 高保真产品原型：[`outputs/apt-hunter-prototype`](./outputs/apt-hunter-prototype)
- 产品与工程设计：[`outputs/apt-hunter-engineering-docs`](./outputs/apt-hunter-engineering-docs)
- 工程状态：进入 M0 工程基座阶段

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

详细需求、接口、数据模型和开发里程碑请从[工程文档索引](./outputs/apt-hunter-engineering-docs/README.md)开始阅读。
