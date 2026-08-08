# M11 备份恢复、监控告警、OpenAPI 与发布工程

更新时间：2026-08-08

## 已交付

- PostgreSQL custom-format 自动备份：安全目录校验、临时文件、dump 清单验证、原子改名、`0600` 权限、SHA-256 和 14 天保留。
- 无损恢复验证：恢复到名称受限的临时数据库，核对迁移与核心表行数，并通过 trap 自动清理。
- 用户级 systemd 定时器：每日执行、随机延迟、错过后补跑；`loginctl linger` 已启用，SSH 退出后仍运行。
- Prometheus 内部采集：HTTP 请求量/耗时/并发、Job 状态、报告状态、Celery 队列深度、来源连续失败与依赖可用性。
- 5 条告警规则：API 离线、依赖离线、队列积压、持久失败作业与来源连续失败。
- OpenAPI 3.1 契约快照与生成/一致性检查脚本。
- CI 门禁：前后端格式、lint、类型、测试、构建，OpenAPI、Compose、Shell、Prometheus 配置和双镜像构建。
- Release 流水线：`v*` 标签或手动触发先运行全量验证，再将 API/Web 的发布标签与完整 Git SHA 推送 GHCR，并生成 SBOM、provenance 与 attestation。
- Compose 支持独立镜像仓库和不可变 `APT_HUNTER_IMAGE_TAG`；API Dockerfile 将依赖层与源码层分开缓存。

## 线上验收

- API、Worker、Beat、Web、PostgreSQL、Redis、MinIO、Prometheus 均运行；API 健康检查通过。
- Prometheus 目标 `api:8000/metrics` 为 `up`，采集到 2 个成功 Job、0 个失败 Job和 0 队列积压。
- Prometheus 配置及 5 条告警规则通过 `promtool check config`。
- 新备份：`/var/backups/apt-hunter/apt-hunter-20260808T125434Z.dump`，101270 字节，dump 与 SHA 文件权限均为 `0600`。
- 恢复演练读取迁移 `20260808_0009`、1 个来源、10 篇报告和 1 个用户，临时数据库随后删除。
- OpenAPI 快照为 185833 字节，并通过生成器 `--check` 一致性验证。
- 自动备份下一次执行时间：2026-08-09 02:15 UTC（带 15 分钟随机延迟）。
- 后端 43 项测试、严格 MyPy、Ruff 全部通过；前端 16 项测试、ESLint、TypeScript 与生产构建通过。

## 边界说明

- Prometheus 仅绑定服务器 `127.0.0.1:9090`，PostgreSQL/Redis/MinIO API 仍未暴露。
- 告警规则已运行，但没有臆造邮件、Slack 等外部收件目标；提供 Alertmanager 接收端后可按运维手册接入。
- GitHub 工作流已静态验证并纳入仓库；只有仓库关联 GitHub 远程并推送后，托管 Runner 与 GHCR 发布才会实际触发。
- CaptiveCrunch 报告仍保持 `pending`，本阶段没有创建或修改情报数据。

## 下一阶段

全页面 E2E、响应式、无障碍、性能、安全扫描、视觉回归和最终发布验收。
