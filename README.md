# APT Hunter

APT Hunter 是一套独立的 AI-first APT 威胁情报采集、分析、狩猎与持续跟踪平台。系统从 RSS、公开网页、X 和 Telegram 收集信息，以可配置大模型完成全量语义分析、证据验证和分级自动决策，将多篇报道归并为去重攻击事件，并按照攻击钻石模型组织攻击者、能力、基础设施和受害目标。人工只处理证据不足、归因冲突和低置信度异常。

## 当前版本

当前稳定版本为 **1.0.0**，核心产品范围已经完成并通过最终验收：

- RSS、公开 Web、X API v2、Telegram Bot API 四类采集连接器
- APT 相关性筛选、正文抽取、去重、钻石模型、Observable 与 ATT&CK 提取
- 可配置 OpenAI 兼容大模型、加密凭据、独立 AI 验证、决策门禁与安全降级
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
docker compose --env-file .env -f compose.yaml up -d --build
./scripts/release-check.sh
./scripts/security-check.sh
./scripts/e2e-live.sh
```

## 部署与启动

### 环境要求

- Ubuntu Server（建议 22.04 LTS 或更高版本）
- Docker Engine 及 Docker Compose v2（`docker compose version` 应可正常执行）
- Git、至少 4 vCPU、8 GB 内存和 40 GB 可用磁盘空间
- 对外开放 Web 端口（默认 `8180`）；PostgreSQL、Redis、MinIO 和 Prometheus 仅在 Compose 网络或本机使用

### 首次部署

在服务器上执行以下命令。将仓库地址和分支替换为实际发布版本；生产环境建议使用提交号作为镜像标签，避免 `latest` 漂移。

```bash
git clone <repository-url> /opt/apt-hunter
cd /opt/apt-hunter
git checkout <release-or-commit>

cp infra/.env.example infra/.env
${EDITOR:-vi} infra/.env
```

至少检查并修改 `infra/.env` 中的数据库、Redis、MinIO 密码和 `APT_HUNTER_AI_SECRETS_KEY`。AI 密钥加密用的 `APT_HUNTER_AI_SECRETS_KEY` 应使用随机生成的稳定值（至少 32 个字符），后续升级不得更换，否则已保存的 AI 凭据无法解密。`.env` 包含敏感信息，禁止提交到 Git。

启动服务并验证：

```bash
cd /opt/apt-hunter/infra
docker compose --env-file .env -f compose.yaml up -d --build
./scripts/release-check.sh
```

通过 `http://<服务器地址>:8180` 访问系统。首次登录后请立即修改管理员密码，并在“系统配置 / AI 自动化”中添加、测试并选择默认模型；AI 策略可按试运行需要启用，低置信度结果会进入人工审核队列。首次启用会自动让启用前已采集、曾被过滤或曾处理失败的材料重新进入 AI 队列；需要重试时可再次点击“历史材料回填”，已确认结果不会被重复覆盖。

### 服务器重启后启动

Compose 使用持久化卷保存 PostgreSQL、MinIO 和 Redis 数据。主机重启后无需重新初始化数据库，也不要执行 `down -v`；进入项目目录重新拉起服务即可：

```bash
cd /opt/apt-hunter/infra
docker compose --env-file .env -f compose.yaml up -d
./scripts/release-check.sh
```

`migrate` 容器正常完成迁移后会退出，这是预期行为；其余 `api`、`worker`、`beat`、`web`、`postgres`、`redis`、`minio` 和 `prometheus` 应显示为 `Up`，其中 API、数据库、Redis 和 MinIO 应为 `healthy`。

### 日常运维

```bash
# 查看服务状态
docker compose --env-file .env -f compose.yaml ps

# 查看核心服务日志（Ctrl-C 退出）
docker compose --env-file .env -f compose.yaml logs -f api worker beat web

# 正常停止和启动（不删除数据卷）
docker compose --env-file .env -f compose.yaml stop
docker compose --env-file .env -f compose.yaml start
```

只有在需要重建网络或容器时才使用 `docker compose ... down`。除非确认要清空全部本地数据，否则不要使用 `down -v`。备份、恢复、健康检查、日志保留和故障排查见 [运维与发布手册](./docs/operations-runbook.md)。

### 更新与回滚

更新前先创建数据库和对象存储备份，然后固定到目标提交并重建服务：

```bash
cd /opt/apt-hunter
git fetch --all --tags
git checkout <target-commit>
export APT_HUNTER_IMAGE_TAG="$(git rev-parse HEAD)"
cd infra
docker compose --env-file .env -f compose.yaml up -d --build
./scripts/release-check.sh
```

如果健康检查失败，查看 `docker compose ... logs`，将代码和 `APT_HUNTER_IMAGE_TAG` 回滚到上一个已验证提交，再重新执行启动和检查命令。不要删除 PostgreSQL/MinIO 数据卷来处理应用升级问题。

详细状态见 [AI 自动化说明](./docs/ai-automation.md)、[1.0.0 发布说明](./docs/m12-status.md)、[交付完成矩阵](./docs/completion-matrix.md)、[运维与发布手册](./docs/operations-runbook.md) 和 [OpenAPI 契约](./docs/api-contract.md)。
