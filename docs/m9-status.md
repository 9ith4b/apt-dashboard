# M9 Web、X 与 Telegram 合规连接器

更新时间：2026-08-08

## 已交付

### 统一采集契约

- RSS、公开 Web、X 官方 API 和 Telegram Bot API 使用同一 Source、持久 Job、报告去重、APT 相关性筛选和失败退避链路。
- 调度器按来源类型派发连接器；手动采集也会创建可追踪 Job，不在 HTTP 请求中执行长任务。
- 连接器统一返回文章条目、下一游标、条件请求信息和供应方建议的下次采集时间。
- 规范 URL、内容哈希和来源 URL 继续复用既有去重规则，避免同一材料重复沉淀。

### 公开 Web

- 仅接受公开 HTTP(S) URL，复用 DNS/IP/跳转逐跳检查和正文体积上限。
- 不执行网页脚本，不绕过登录、验证码、反爬或付费墙。
- 抽取到的正文进入与 RSS 相同的报告分析管线。

### X 官方 API

- 使用 X API v2 `tweets/search/recent`，支持查询表达式、`since_id` 增量游标和每批 10–100 条限制。
- 使用响应 `newest_id` 推进游标，并根据官方 rate-limit reset 响应头延后下一次采集。
- 只保存公开 Tweet 文本、作者 ID、发布时间和官方 Tweet URL。

### Telegram Bot API

- 使用官方 `getUpdates`，只处理 Source 中显式允许的 `chat_ids`。
- 使用 update offset 增量游标；不读取 Bot 未获授权的频道，也不使用用户会话或规避平台限制。
- 对公开频道生成 `t.me/<username>/<message_id>` 链接；私有频道保留可审计的内部消息标识。

### 凭据边界

- X 只允许引用 `APT_HUNTER_X_BEARER_TOKEN`，Telegram 只允许引用 `APT_HUNTER_TELEGRAM_BOT_TOKEN`。
- Token 只从 API/Worker 服务环境变量解析，不写入 Source 配置、不通过 API 返回、不在前端输入。
- 配置中出现 token、secret 或 password 字段会被拒绝；前端只显示“已配置/待配置”。

## 配置方法

在 `/opt/apt-hunter/infra/.env` 中按需设置：

```dotenv
APT_HUNTER_X_BEARER_TOKEN=<X API v2 bearer token>
APT_HUNTER_TELEGRAM_BOT_TOKEN=<Telegram bot token>
```

然后只重建需要读取环境变量的服务：

```bash
cd /opt/apt-hunter/infra
docker compose up -d --build api worker beat
```

在“数据源 → 添加数据源”中选择连接器类型：

- X：填写名称、官方 API 查询语句和采集间隔。
- Telegram：填写名称、逗号分隔的频道 ID/用户名和采集间隔，并先把 Bot 加入目标频道。
- 公开 Web：填写无需登录即可访问的文章 URL。

## API 与数据模型

- `POST /api/v1/sources` 的 `type` 支持 `rss | web | x | telegram`。
- `url` 用于 RSS/Web；`config.query` 用于 X；`config.chat_ids` 用于 Telegram。
- `secret_ref` 只能使用上面的固定环境变量名；读取响应不返回该字段。
- `credential_configured` 仅表示对应服务端环境变量是否存在，不泄漏值。
- 无数据库迁移：复用 Source 既有 `config` JSON 与 `secret_ref` 字段。

## 质量与上线验证

- 后端：36 项测试通过，Ruff、格式检查与严格 MyPy 通过。
- 前端：14 项交互测试通过，Prettier、ESLint、TypeScript 与生产构建通过。
- 覆盖：X 查询/游标/限速时间、Telegram 频道过滤/offset、四类 Source 契约、配置敏感字段拒绝、前端 X 创建载荷不含凭据。
- 浏览器：生产数据源页显示真实 RSS 健康状态与 10 篇报告；四类表单及 X 凭据说明可见，控制台无错误，未创建测试数据。
- 服务：API、Worker、Beat、PostgreSQL、Redis、MinIO 全部健康，就绪检查 4/4。
- 线上地址：`http://server.example.com:8180`

## 当前生产凭据状态

X 与 Telegram Token 尚未配置，因此未创建或启用社交连接器。现有 Microsoft Security Blog RSS 继续正常采集。真实 CaptiveCrunch 材料仍保持 `pending`，自动验收没有替分析员批准或变更该材料。

## 下一开发增量

1. 登录会话、角色权限、CSRF、审计日志和安全响应头。
2. SSRF/MIME/压缩比/错误脱敏边界回归与限流防滥用。
3. 自动备份恢复、指标告警、CI/CD、OpenAPI 与最终发布验收。
