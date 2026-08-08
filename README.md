# APT Hunter

APT Hunter 是一套独立的 APT 威胁情报采集、分析、审核、狩猎与持续跟踪平台。系统从 RSS、公开网页、X 和 Telegram 收集信息，将多篇报道归并为去重攻击事件，并按照攻击钻石模型组织攻击者、能力、基础设施和受害目标。所有自动结论保留原文证据，重要结果经人工审核后才进入知识库。

## 当前版本

当前稳定版本为 **1.0.0**，核心产品范围已经完成并通过最终验收：

- RSS、公开 Web、X API v2、Telegram Bot API 四类采集连接器
- APT 相关性筛选、正文抽取、去重、钻石模型、Observable 与 ATT&CK 提取
- 人工审核、版本化威胁事件、相似事件聚类、合并/驳回/撤销
- 威胁组织持续跟踪，支持月、年、全部和自定义日期，含周期对比及 JSON/CSV 导出
- Observable 检索、本地富化、人工提升 Indicator，以及 Campaign 时间线
- 关注规则、站内通知、全局搜索、持久作业中心和审计日志
- Argon2id 身份认证、HttpOnly 会话、CSRF、RBAC、登录限流与安全响应头
- PostgreSQL/Redis/Celery/MinIO/Prometheus、备份恢复、告警规则、OpenAPI、CI 与 GHCR 发布流水线
- 桌面与移动端 E2E、WCAG、性能、视觉回归、安全依赖审计和构建体积门禁

部署地址：`http://server.example.com:8180`

初始管理员密码仅保存在服务器的 `/etc/apt-hunter/admin-initial-password`（权限 `0600`）。首次登录后应立即修改密码。

## 技术基线

- Web：React、TypeScript、Vite、Tailwind CSS、shadcn/ui
- API：FastAPI、Pydantic、SQLAlchemy、Alembic
- 数据与任务：PostgreSQL、Redis、Celery、MinIO
- 运维：Docker Compose、Prometheus、systemd timer、GitHub Actions

## 目录

```text
apps/web/       React 前端、单元测试和 Playwright E2E
apps/api/       FastAPI 服务、Worker、迁移和测试
infra/          Compose、Prometheus、备份恢复与发布脚本
docs/           API 契约、运维手册、里程碑和发布记录
outputs/        原型与早期工程设计文档
```

## 开发与验证

```bash
pnpm install --frozen-lockfile
pnpm --filter web format:check
pnpm --filter web lint
pnpm --filter web typecheck
pnpm --filter web test
pnpm --filter web build
pnpm --filter web budget
```

```bash
cd apps/api
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest
.venv/bin/mypy src
.venv/bin/python scripts/export_openapi.py --check
```

```bash
cp infra/.env.example infra/.env
cd infra
docker compose up -d --build
./scripts/release-check.sh
./scripts/security-check.sh
./scripts/e2e-live.sh
```

详细状态见 [1.0.0 发布说明](./docs/m12-status.md)、[交付完成矩阵](./docs/completion-matrix.md)、[运维与发布手册](./docs/operations-runbook.md) 和 [OpenAPI 契约](./docs/api-contract.md)。
