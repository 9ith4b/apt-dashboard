# APT Hunter 工程设计文档

APT Hunter 是一个独立建设的威胁情报采集、分析、审核与持续跟踪系统。系统从 RSS、公开网页、X 和 Telegram 等来源收集与 APT 相关的信息，将多篇报道归并为攻击事件，并按照攻击钻石模型组织攻击者、能力、基础设施和受害目标。

## 文档导航

1. [产品需求](./01-product-requirements.md)
2. [信息架构](./02-information-architecture.md)
3. [交互与设计系统](./03-interaction-and-design-system.md)
4. [系统架构](./04-system-architecture.md)
5. [数据模型](./05-data-model.md)
6. [采集与分析管道](./06-ingestion-and-analysis-pipeline.md)
7. [API 契约](./07-api-contract.md)
8. [安全、部署与运维](./08-security-deployment-operations.md)
9. [测试、验收与交付路线](./09-testing-and-delivery.md)

## 产品基线

- 前端：React、TypeScript、Vite、React Router、TanStack Query、Tailwind CSS、shadcn/ui、Recharts。
- 后端：FastAPI、PostgreSQL、Redis、Celery、MinIO。
- 使用方式：首版为单用户本地账户。
- 自动分析：确定性规则与词典负责 IOC 和显式实体，可插拔 LLM 负责语义归纳；所有重要结论都需要证据，并允许人工审核。
- 时间显示：默认 `Asia/Shanghai`，数据库统一保存 UTC。
- 统计口径：报道和攻击事件分别统计，多篇报道描述同一攻击时只形成一条去重事件。

## 原型对应关系

| 页面 | 原型文件 | 主要职责 |
| --- | --- | --- |
| 情报流 | [`01-intelligence-feed.png`](../apt-hunter-prototype/01-intelligence-feed.png) | 查看新采集内容、相关性和事件候选 |
| 事件钻石 | [`02-event-diamond.png`](../apt-hunter-prototype/02-event-diamond.png) | 分析攻击者、能力、基础设施和受害目标 |
| 事件审核 | [`03-event-review.png`](../apt-hunter-prototype/03-event-review.png) | 对照原文证据审核自动提取结果 |
| 攻击者画像 | [`04-actor-profile.png`](../apt-hunter-prototype/04-actor-profile.png) | 查看组织别名、TTP、目标和行为变化 |
| Campaign 时间线 | [`05-campaign-timeline.png`](../apt-hunter-prototype/05-campaign-timeline.png) | 按阶段组织连续攻击活动 |
| IOC 狩猎 | [`06-ioc-hunting.png`](../apt-hunter-prototype/06-ioc-hunting.png) | 搜索、富化并提升 Observable |
| 审核队列 | [`07-review-queue.png`](../apt-hunter-prototype/07-review-queue.png) | 处理归因、实体合并、IOC 和事件候选 |
| 数据源管理 | [`08-source-management.png`](../apt-hunter-prototype/08-source-management.png) | 配置采集源、凭据状态和运行健康度 |
| 关注规则 | [`09-watch-rules.png`](../apt-hunter-prototype/09-watch-rules.png) | 配置组织、行业、技术和关键词关注条件 |
| 持续跟踪 | [`10-apt-continuous-tracking-custom-range.png`](../apt-hunter-prototype/10-apt-continuous-tracking-custom-range.png) | 按月、年或自定义日期跟踪单个 APT 组织 |

## 共同术语

- **Raw Document**：从外部来源取得的原始内容及抓取元数据。
- **Report**：清洗并可供分析的单篇报道。
- **Threat Event**：由一篇或多篇报道共同描述的去重攻击事件。
- **Campaign**：具有共同目标、能力或时间连续性的多个攻击事件集合。
- **Observable**：被观察到的值，例如 IP、域名、URL、哈希或邮箱，本身不必然恶意。
- **Indicator**：有恶意证据、用途和有效期，可用于检测或狩猎的指标。
- **Evidence**：支持某个字段或关系的来源片段、位置和原文链接。

## 文档状态

当前版本用于 MVP 工程立项与开发。任何影响接口、统计口径或审核流程的变更，都应先修改相应文档并记录版本。
