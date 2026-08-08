# M2 正文富化与人工复核状态

更新时间：2026-08-08

## 已交付

### 采集与候选筛选

- RSS/Atom 数据源增删改、启停、手动采集和定时采集。
- ETag、Last-Modified、304 支持，规范 URL 与正文摘要哈希去重。
- 基于攻击组织和攻击语义的 APT 相关性评分。
- SSRF 防护、重定向逐跳校验、失败退避和数据源健康状态。
- 被过滤的普通安全文章保留在数据库中用于审计，但不进入主情报流。

### 正文与钻石模型

- 候选文章由 Celery Beat 自动发现并加入富化队列。
- 使用 Trafilatura 提取网页主要正文，限制响应类型、体积、超时和重定向次数。
- 规则引擎拆解四个维度：
  - 对手：APT、UNC、FIN、STORM、DEV 编号及常见组织别名。
  - 能力：钓鱼、恶意软件投递、凭据窃取、漏洞利用、供应链、勒索、社会工程和 C2。
  - 基础设施：带上下文约束的 URL、域名和公网 IP。
  - 受害者：行业与角色类别。
- 每个实体保留置信度与原文证据；未找到的维度保持为空，不自动补全。
- 正文、提取结果、内容哈希、方法版本、错误和处理时间持久化。

### 人工复核

- 待审核、已通过、已驳回三个队列。
- 材料详情展示完整正文、四维实体和证据索引。
- 支持分析员备注、通过、驳回和重新富化。
- 审核使用乐观锁版本号，过期页面不能覆盖较新的决定。
- 情报流与审核页面均使用真实 API 数据，不再使用演示材料。

## 线上验证

真实 Microsoft Security Blog 文章 `CaptiveCrunch: Midnight Blizzard targets travelers worldwide for malware delivery and credential theft` 已完成端到端验证：

- 正文提取状态：`ready`
- 自动置信度：`95`
- 对手：Midnight Blizzard / APT29、STORM-2945 等候选实体
- 能力：Phishing、Malware delivery、Credential theft、Social engineering、Command and control
- 基础设施：3 个恶意端点 URL、6 个公网 IP
- 受害者：Government、Diplomats、Hospitality、Travelers
- 审核状态：`pending`

数据库迁移已到 `20260808_0003`。API、Worker、Beat、Web、PostgreSQL、Redis 和 MinIO 均健康运行。

## API 概览

- `GET /api/v1/reports`：材料列表与富化/审核状态。
- `GET /api/v1/reports/{report_id}`：正文、钻石实体和证据详情。
- `POST /api/v1/reports/{report_id}/enrich`：重新加入富化队列。
- `GET /api/v1/reviews?review_status=pending`：审核队列。
- `POST /api/v1/reviews/{report_id}/decision`：提交版本化审核决定。

## 质量保障

- 后端：21 项测试通过，Ruff 与严格 MyPy 检查通过。
- 前端：6 项交互测试通过，ESLint、TypeScript 和生产构建通过。
- 浏览器：桌面与 375px 移动宽度验证通过，无横向溢出或控制台错误。
- 真实任务：Beat 自动调度查询和 Worker 正文富化均在 PostgreSQL 环境执行成功。

## 当前边界与下一阶段

当前提取结果是“供分析员确认的候选结论”，不是未经审核即可对外发布的最终情报。规则引擎能够提供低维护、无外部模型密钥的基线，但上下文归因仍可能同时提取文章中用于比较的关联组织。

下一阶段建议按顺序推进：

1. 字段级编辑、保留/排除和审核记录，让分析员可修正单个实体而非只审核整篇材料。
2. 将审核后的材料归并为 `ThreatEvent`，实现同一事件的多来源聚类与时间线。
3. 提取文件哈希、CVE、MITRE ATT&CK 技术与地理信息，并接入被动 DNS、WHOIS、恶意样本等富化器。
4. 建立攻击组织画像与自定义日期跟踪页，按月、年统计已确认攻击事件。
5. 增加受控的 X、Telegram 等社交媒体采集适配器。
6. 在规则引擎之后提供可选 LLM 分析器，但继续强制输出证据与人工审核。
