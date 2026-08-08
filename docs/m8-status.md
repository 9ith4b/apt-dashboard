# M8 关注规则、通知、全局搜索与持久 Job 状态

更新时间：2026-08-08

## 已交付

### 结构化关注规则

- 规则 DSL 由关键词、攻击组织、Observable 类型、ATT&CK 技术和最低置信度组成，不接受或执行任意用户表达式。
- 不同字段按 AND、同字段多值按 OR 匹配；只有已确认且未被合并替代的事件会进入评估。
- 新规则可在写入前预览已有事件；已保存规则可再次预览，预览不会创建命中或通知。
- “运行并记录命中”使用规则—对象唯一约束防止重复；新事件在人工审核确认事务中自动评估已启用规则。
- 规则启停和更新使用版本检查，防止并发覆盖。

### 命中与站内通知

- 命中记录保存事件、命中字段和值及创建时间，可从规则页面跳转回事件证据。
- 每个命中只生成一条通知，保留严重度、目标对象和已读时间。
- 顶部通知抽屉显示未读数量，支持逐条已读与全部已读。

### 全局搜索

- 顶部搜索聚合 Threat Actor（含别名）、Threat Event、Observable 和 Report。
- 按精确、前缀、标题包含及摘要包含进行确定性排序，返回对象类型、摘要和产品内快捷链接。
- 最少输入两个字符且限制结果数量，避免空查询扫描。

### 持久 Job 与作业中心

- 手动或定时 RSS 采集、手动或定时报告富化都会先创建持久 Job，再使用同一任务 ID 投递 Celery。
- Worker 在开始、成功或失败时更新进度、结果、错误和时间戳；已取消 Job 不会被迟到的 Worker 结果覆盖。
- 取消采用 Celery revoke 非强制终止语义，避免中断正在提交的数据库事务。
- 失败或已取消作业可创建带父 Job 和递增 attempt 的重试记录。
- 作业中心按状态筛选并每 5 秒刷新，展示对象、尝试次数、进度、错误及允许的操作。

## API 概览

- `GET/POST/PATCH/DELETE /api/v1/watch-rules`：规则管理与版本保护。
- `POST /api/v1/watch-rules/preview`、`POST /api/v1/watch-rules/{id}/preview`：无副作用预览。
- `POST /api/v1/watch-rules/{id}/evaluate`、`GET /api/v1/watch-rules/{id}/hits`：持久评估和命中查询。
- `GET/PATCH/POST /api/v1/notifications...`：通知列表、逐条和全部已读。
- `GET /api/v1/search?q=...`：跨四类知识对象搜索。
- `GET /api/v1/operations/jobs`、`POST .../cancel|retry`：作业查询、取消与重试。

## 数据库变更

迁移版本：`20260808_0008`

- 新增 Watch Rule、Watch Rule Hit、Notification 与 Operation Job 表。
- 使用命中唯一约束、通知唯一约束、任务 ID 唯一约束、状态/进度检查、版本列及查询索引保护一致性。
- 迁移前备份：`/var/backups/apt-hunter/pre-m8-20260808-113200.dump`。

## 质量与上线验证

- 后端：33 项测试通过，Ruff、格式检查与严格 MyPy 通过。
- 前端：13 项交互测试通过，Prettier、ESLint、TypeScript 与生产构建通过。
- 覆盖：自动命中、预览无副作用、去重、通知已读、Actor 别名搜索、Observable/Report 搜索、Job 持久化、取消和重试；规则/作业页面及全局搜索交互。
- 浏览器：关注规则与作业中心已替换占位页，生产空状态和新增导航正常，控制台无 error/warning；搜索 API 在真实 CaptiveCrunch 报告上返回结果。
- 服务：API、Worker、Beat、PostgreSQL、Redis、MinIO 全部健康，迁移为 `20260808_0008 (head)`。
- 线上地址：`http://server.example.com:8180`

## 当前生产数据状态

真实 CaptiveCrunch 材料继续保持 `pending`。因此线上规则、命中、通知和 Job 当前为空；搜索可以只读找到该报告。自动验收没有创建规则、触发作业或替分析员批准材料。

## 下一开发增量

1. 通用 Web、X 和 Telegram 连接器，统一游标、限速、凭据引用与契约测试。
2. 登录会话、角色权限、CSRF、审计和剩余 SSRF/抓取边界加固。
3. 自动备份恢复、指标告警、CI/CD、OpenAPI 与发布验收。
