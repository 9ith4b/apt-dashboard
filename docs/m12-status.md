# M12 / 1.0.0 最终发布状态

日期：2026-08-08

## 结论

APT Hunter 1.0.0 的既定产品与工程范围已经完成。生产栈部署在 `http://server.example.com:8180`，API 健康端点返回 `version: 1.0.0`。应用使用 Git 提交 SHA 作为不可变镜像标签，发布前后均由自动化脚本校验迁移、健康状态、核心页面和安全响应头。

## 最终验收

- API：43 个 pytest 用例通过；Ruff format/check、strict mypy、OpenAPI 契约检查通过。
- Web：16 个 Vitest 用例通过；Prettier、ESLint、TypeScript、生产构建通过。
- 构建体积：最大 JS chunk 小于 450 KiB、JS 总量小于 700 KiB、CSS 小于 120 KiB。
- 安全：`pnpm audit --audit-level high`、Bandit 和 `pip-audit` 均无已知漏洞或代码发现。
- E2E：验证登录与会话、10 个核心页面、无浏览器控制台错误、无横向溢出、移动导航、WCAG、页面性能和两张稳定视觉基线。
- 实测性能：最终远程局域网回归中认证后应用壳页面 `domInteractive` 约 36 ms、`load` 约 68 ms。
- 运维：Prometheus 目标为 UP；5 条告警规则加载；全量备份、SHA-256 校验和隔离恢复演练通过。

Playwright 定义 14 条跨项目场景；按 desktop/mobile 项目适用性执行 9 条，5 条为配置中明确的项目互斥跳过，并非失败。

## 数据安全确认

- 现有真实 CaptiveCrunch 报告保持待审核，没有因验收而批准、重新富化、生成事件、Campaign、规则、作业或数据源。
- X 与 Telegram 连接器实现已完成，但生产环境只有在管理员配置官方 API 凭据后才会主动采集。
- Prometheus 仅监听服务器回环地址；MinIO 控制台也仅监听回环地址。
- 当前部署面向可信内网，使用 HTTP，因此 `secure_cookie=false`。迁移至 HTTPS 时必须设置 `secure_cookie=true`，并由反向代理终止 TLS。
- 外部 Alertmanager 收件目标尚未提供；Prometheus 告警规则已生效，外部通知需在取得目标后配置。

## 运行与维护

- 初始管理员密码文件：`/etc/apt-hunter/admin-initial-password`，权限 `0600`；首次使用后立即轮换。
- 每日备份由用户级 systemd timer 执行，保留 14 天；恢复命令见 `docs/operations-runbook.md`。
- GitHub Actions 已定义 CI、E2E、安全审计、镜像发布、SBOM 与 provenance。当前仓库没有获准推送到远端，因此托管工作流未被触发；本机等价检查均已通过。

## 发布制品

- `docs/openapi.json`：1.0.0 OpenAPI 快照。
- `apps/web/e2e/*`：桌面、移动端、可访问性、性能和视觉测试。
- `infra/scripts/release-check.sh`：上线验收。
- `infra/scripts/security-check.sh`：依赖与静态安全检查。
- `infra/scripts/e2e-live.sh`：容器化浏览器验收。
- `infra/scripts/backup.sh` 与 `restore-verify.sh`：备份和隔离恢复验证。
