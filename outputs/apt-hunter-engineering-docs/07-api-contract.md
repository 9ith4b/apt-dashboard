# API 契约

## 1. 通用约定

- 基础路径：`/api/v1`。
- 数据格式：`application/json; charset=utf-8`。
- 时间：ISO 8601 UTC；日期筛选同时传递 IANA 时区。
- 分页：游标分页，参数 `cursor`、`limit`，默认 50，最大 200。
- 写操作通过 `Idempotency-Key` 支持安全重试。
- OpenAPI 是前后端类型的唯一接口来源，前端类型由其生成。

成功列表响应：

```json
{
  "items": [],
  "next_cursor": null,
  "total_estimate": 0
}
```

错误响应：

```json
{
  "error": {
    "code": "validation_error",
    "message": "可供用户理解的错误说明",
    "details": [],
    "request_id": "uuid"
  }
}
```

## 2. 公共类型

```ts
type ReviewStatus = "candidate" | "confirmed" | "rejected" | "superseded";
type EventStatus = "candidate" | "in_review" | "confirmed" | "rejected" | "superseded";
type EvidenceType = "direct" | "indirect" | "contradicting" | "analyst";
type TimeBucket = "day" | "week" | "month" | "auto";

interface DateRange {
  from: string;       // YYYY-MM-DD
  to: string;         // YYYY-MM-DD，用户可见的包含式结束日期
  timezone: string;   // 默认 Asia/Shanghai
}

interface EvidenceRef {
  id: string;
  report_id: string;
  quote: string;
  locator?: string;
  evidence_type: EvidenceType;
  source_url: string;
}

interface ConfidenceAssessment {
  automatic?: number;
  analyst?: number;
  effective: number;
  rationale?: string;
}

interface DiamondFacet<T> {
  entity: T;
  review_status: ReviewStatus;
  confidence: ConfidenceAssessment;
  evidence: EvidenceRef[];
}
```

## 3. 认证

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/auth/login` | 建立 HttpOnly 会话 |
| `POST` | `/auth/logout` | 注销当前会话 |
| `GET` | `/auth/me` | 当前账户与会话信息 |
| `GET` | `/auth/csrf` | 获取写操作 CSRF token |

登录失败统一返回通用消息，不泄露账户是否存在。连续失败触发按 IP 和账户的限速。

## 4. 情报流与报道

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/feed` | 按来源、相关性、状态和日期查询 |
| `GET` | `/reports/{id}` | 报道详情和分析状态 |
| `GET` | `/reports/{id}/content` | 规范正文及证据定位信息 |
| `POST` | `/reports/{id}/reanalyze` | 用当前分析版本重新处理 |
| `POST` | `/reports/{id}/ignore` | 忽略或恢复 |

`GET /feed` 主要参数：`source_id`、`min_relevance`、`status`、`actor_id`、`from`、`to`、`timezone`、`sort`。

## 5. 事件与钻石模型

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/events` | 查询事件 |
| `POST` | `/events` | 手工创建事件候选 |
| `GET` | `/events/{id}` | 事件、钻石实体、关系和来源 |
| `PATCH` | `/events/{id}` | 编辑允许修改的事件字段 |
| `POST` | `/events/{id}/reports` | 关联报道 |
| `DELETE` | `/events/{id}/reports/{reportId}` | 解除关联，不删除报道 |
| `POST` | `/events/{id}/merge` | 创建事件合并版本 |
| `POST` | `/events/{id}/undo-merge` | 撤销最近可撤销合并 |

所有 `PATCH` 请求包含 `version`。版本不匹配返回 `409 version_conflict` 和当前版本摘要。

事件详情核心响应：

```json
{
  "id": "uuid",
  "version": 3,
  "title": "Lazarus 虚假面试活动",
  "status": "confirmed",
  "first_seen": "2026-07-01T00:00:00Z",
  "last_seen": "2026-07-18T00:00:00Z",
  "adversaries": [],
  "capabilities": [],
  "infrastructure": [],
  "victims": [],
  "relationships": [],
  "reports": []
}
```

## 6. 审核

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/reviews` | 审核队列 |
| `GET` | `/reviews/{id}` | 任务、候选差异和证据 |
| `POST` | `/reviews/{id}/draft` | 保存草稿 |
| `POST` | `/reviews/{id}/decisions` | 提交字段级决策 |
| `POST` | `/reviews/{id}/complete` | 完成并校验审核 |
| `POST` | `/reviews/{id}/reopen` | 重新打开 |

字段级决策：

```json
{
  "subject_id": "uuid",
  "field_path": "adversaries[0].entity",
  "action": "accept",
  "value": null,
  "confidence": 85,
  "reason": "两条直接证据明确归因"
}
```

`action` 为 `accept`、`modify` 或 `reject`。修改必须提供 `value`，拒绝必须提供原因。

## 7. 攻击者、Campaign 与跟踪

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/actors` | 搜索攻击者和别名 |
| `GET` | `/actors/{id}` | 画像、TTP、目标和变化 |
| `GET` | `/campaigns` | Campaign 列表 |
| `GET` | `/campaigns/{id}` | 阶段时间线和事件 |
| `GET` | `/actors/{id}/tracking` | 日期范围内持续跟踪数据 |
| `POST` | `/actors/{id}/tracking/summary` | 生成摘要草稿 |
| `POST` | `/actors/{id}/tracking/export` | 创建异步导出任务 |

跟踪查询示例：

```text
GET /api/v1/actors/{id}/tracking
  ?from=2026-01-01
  &to=2026-03-31
  &timezone=Asia/Shanghai
  &bucket=auto
  &status=confirmed,candidate
```

`bucket=auto`：不超过 31 天为 `day`，32–180 天为 `week`，超过 180 天为 `month`。响应必须回显实际桶粒度、解析后的 UTC 区间和统计口径。

## 8. Observable、Indicator 与富化

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/observables` | 精确、批量或模糊查询 |
| `GET` | `/observables/{id}` | 时间线、事件和富化结果 |
| `POST` | `/observables/{id}/enrich` | 创建富化任务 |
| `POST` | `/observables/{id}/promote` | 创建 Indicator 提升审核 |
| `GET` | `/indicators` | 查询 Indicator |
| `PATCH` | `/indicators/{id}` | 更新有效期、撤销状态等 |

提升请求至少包含 `purpose`、`valid_from`、`valid_until`、`confidence` 和 `evidence_ids`。

## 9. 数据源

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET` | `/sources` | 列表和健康状态 |
| `POST` | `/sources` | 创建但默认不启用 |
| `PATCH` | `/sources/{id}` | 更新非敏感配置 |
| `POST` | `/sources/{id}/secret` | 写入或替换凭据引用 |
| `POST` | `/sources/{id}/test` | 测试连接 |
| `POST` | `/sources/{id}/sync` | 手动创建同步任务 |
| `POST` | `/sources/{id}/enable` | 启用调度 |
| `POST` | `/sources/{id}/disable` | 停用调度 |

连接测试返回 DNS、认证、权限、限速和内容解析的分阶段结果，不回显密钥。

## 10. 关注规则、任务与运维

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `GET/POST` | `/watch-rules` | 查询或创建规则 |
| `PATCH` | `/watch-rules/{id}` | 更新规则和版本 |
| `POST` | `/watch-rules/{id}/preview` | 在历史数据上预览命中 |
| `GET` | `/jobs/{id}` | 异步任务进度和结果 |
| `POST` | `/jobs/{id}/retry` | 从安全阶段重试 |
| `GET` | `/health/live` | 进程存活 |
| `GET` | `/health/ready` | 数据库、Redis、对象存储可用性 |
| `GET` | `/audit-logs` | 查询操作审计 |

## 11. 状态码

- `400`：业务参数不可接受；
- `401`：未登录或会话失效；
- `403`：CSRF、敏感操作或策略拒绝；
- `404`：对象不存在；
- `409`：版本冲突、唯一约束冲突或不可合并；
- `422`：Schema 校验失败；
- `429`：用户操作或外部配额限速；
- `503`：依赖暂时不可用，同时提供可重试标识。
