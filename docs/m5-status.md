# M5 情报知识核心与事件合并审核状态

更新时间：2026-08-08

## 已交付

### Observable 与证据链

- 从报告正文确定性提取 URL、域名、IPv4、邮箱、文件哈希和 CVE，保存原值、规范值、范围、置信度、证据原文及字符偏移。
- 普通或私网 Observable 不会因为“被提取”自动变成恶意 Indicator，避免把内部地址和文章引用误报成 IOC。
- 报告级知识在富化事务内写入；事件批准、合并和撤销时同步重建事件级聚合。
- PostgreSQL 使用原子 upsert，并以唯一约束、外键和反向查询索引保护去重与关联完整性。

### MITRE ATT&CK 证据映射

- 识别 `T####` 与 `T####.###` 技术编号并保留字段级引用。
- 报告分析、事件列表与事件详情 API 均返回 ATT&CK 结果。
- 事件页展示技术编号、名称、置信度和原文证据，可用于后续狩猎查询与人工校正。

### 相似事件审核与可逆合并

- 基于共同攻击者、Observable、ATT&CK 技术、受害目标、时间距离和标题相似度生成候选分数。
- 达到阈值只创建人工审核候选，系统不会自动合并事件。
- 分析员可查看相似度构成并确认或驳回；确认后只移动报告归属，原报告、Evidence 和知识对象均保留。
- 已确认合并可按精确报告列表撤销，恢复原事件并重新聚合攻击者、Observable 和 ATT&CK。
- 候选与事件使用版本检查及数据库行锁，避免并发重复决策和交叉合并。

## API 概览

- `GET /api/v1/events`：返回 Observable 数量与 ATT&CK 技术编号摘要。
- `GET /api/v1/events/{event_id}`：返回钻石模型、报告、Observable、ATT&CK 与证据。
- `GET /api/v1/events/merge-candidates?candidate_status=...`：查询待审核、已合并、已驳回或已撤销记录。
- `POST /api/v1/events/merge-candidates/{id}/decision`：确认或驳回候选。
- `POST /api/v1/events/merge-candidates/{id}/undo`：撤销已确认合并。

## 数据库变更

迁移版本：`20260808_0006`

- 新增 Evidence、Observable、报告/事件 Observable 关联表。
- 新增 ATT&CK 技术及报告/事件技术关联表。
- 新增事件合并候选表和事件 `superseded_by_id` 自关联。
- 迁移前备份：`/var/backups/apt-hunter/pre-m5-20260808-102105.dump`。

## 质量与上线验证

- 后端：28 项测试通过，Ruff、格式检查与严格 MyPy 通过。
- 前端：8 项交互测试通过，Prettier、ESLint、TypeScript 与生产构建通过。
- 覆盖：确定性提取、私网边界、知识持久化、事件详情、候选生成、确认、驳回、并发版本冲突和撤销。
- 浏览器：事件空状态、审核入口和现有待审核报告均正常；控制台无 error/warning。
- 服务：API、PostgreSQL、Redis、MinIO 全部健康，迁移为 `20260808_0006 (head)`。
- 线上地址：`http://server.example.com:8180`

## 当前生产数据状态

真实 Microsoft Security Blog 材料 CaptiveCrunch 仍保持 `pending`，未在自动验收中替分析员批准。线上暂时没有已确认事件和合并候选；有数据状态及合并审核由前后端自动化测试覆盖。

## 下一开发增量

1. IOC/Indicator 狩猎工作台、生命周期与富化状态。
2. Campaign 聚合、阶段时间线和事件关联。
3. 关注规则、命中记录、通知与全局搜索。
4. Web、X、Telegram 连接器与采集任务可观测性。
5. 身份认证、审计、备份恢复、指标告警和发布加固。
