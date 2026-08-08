# M6 IOC 狩猎与 Campaign 状态

更新时间：2026-08-08

## 已交付

### Observable 与 Indicator 狩猎

- IOC 页面已替换占位页，可按值和类型检索域名、IPv4、URL、邮箱、哈希及 CVE Observable。
- Observable 详情聚合原始报告、已确认事件、Evidence、Indicator 与富化记录，明确区分“被观察到的事实”和“已研判恶意的 Indicator”。
- 本地上下文富化只使用平台已有数据，不向外部提供商泄露 Observable；结果按提供商保存并支持有效期。
- 提升 Indicator 必须人工填写用途、有效期、置信度和严重度，并选择支持结论的 Evidence；缺少证据会被 API 拒绝。
- Indicator 使用规范模式和版本检查，支持撤销、恢复及并发冲突保护；同一 Observable 不会重复创建多个当前 Indicator。

### Campaign 人工聚合

- Campaign 页面已替换占位页，可创建长期行动容器并查看事件数量、时间范围和阶段分布。
- 只有已确认且当前有效的威胁事件可以加入 Campaign。
- 每次归属都要求分析员填写攻击阶段、置信度和证据说明，避免系统根据相似性自动下结论。
- 阶段时间线保留操作人和归属时间，事件关联可由分析员版本化、可逆移除。

## API 概览

- `GET /api/v1/observables`、`GET /api/v1/observables/{id}`：检索 Observable 并查看报告、事件、Evidence、富化和 Indicator 上下文。
- `POST /api/v1/observables/{id}/enrich`：执行不出网的本地上下文富化。
- `POST /api/v1/observables/{id}/promote`：基于选定证据人工提升 Indicator。
- `GET /api/v1/indicators`、`PATCH /api/v1/indicators/{id}`：查询并版本化维护 Indicator 生命周期。
- `GET/POST /api/v1/campaigns`、`GET/PATCH /api/v1/campaigns/{id}`：查询、创建和维护 Campaign。
- `POST/DELETE /api/v1/campaigns/{id}/events`：人工添加或移除事件归属。

## 数据库变更

迁移版本：`20260808_0007`

- 新增 Indicator、Indicator Evidence 和 Observable Enrichment。
- 新增 Campaign 与 Campaign Event 关联，保存人工阶段、置信度、证据说明和审核人。
- 使用唯一约束、反向查询索引、行锁和版本列保护重复写入及并发更新。
- 迁移前备份：`/var/backups/apt-hunter/pre-m6-20260808-104919.dump`。

## 质量与上线验证

- 后端：30 项测试通过，Ruff、格式检查与严格 MyPy 通过。
- 前端：10 项交互测试通过，Prettier、ESLint、TypeScript 与生产构建通过。
- 覆盖：Observable 检索与上下文、无证据拒绝、提升去重、撤销/恢复、版本冲突、Campaign 创建、归属、阶段、证据、操作人及移除。
- 浏览器：IOC 与 Campaign 页面均已替换占位页，空状态正确、控制台无 error/warning；创建表单由前端交互测试覆盖，线上验收未提交真实数据。
- 服务：API、PostgreSQL、Redis、MinIO 全部健康，迁移为 `20260808_0007 (head)`。
- 线上地址：`http://server.example.com:8180`

## 当前生产数据状态

真实 Microsoft Security Blog 材料 CaptiveCrunch 仍保持 `pending`，未在自动验收中替分析员批准。它早于 rules-v2 富化，因此线上 Observable、Indicator 与 Campaign 当前为空；完整有数据流程由自动化测试覆盖。

## 下一开发增量

1. 攻击组织持续跟踪的周期对比、变化提示、摘要和导出。
2. 关注规则、命中记录、通知、全局搜索和持久 Job 工作台。
3. Web、X、Telegram 连接器及采集可靠性。
4. 身份认证、审计、备份恢复、指标告警和发布加固。
