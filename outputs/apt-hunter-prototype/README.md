# APT Hunter 高保真原型

视觉方向：钻石模型画布（方案 3）。

技术实现约束：React、TypeScript、Tailwind CSS、shadcn/ui。

## 页面清单

1. `01-intelligence-feed.png`：情报流与高相关事件速览
2. `02-event-diamond.png`：事件钻石模型与对象详情
3. `03-event-review.png`：原文证据与结构化结果审核
4. `04-actor-profile.png`：攻击者画像、行为变化与高置信关系
5. `05-campaign-timeline.png`：Campaign 阶段时间线与阶段证据
6. `06-ioc-hunting.png`：Observable/Indicator 搜索、富化与提升
7. `07-review-queue.png`：归因、IOC、实体合并与相关性审核队列
8. `08-source-management.png`：RSS、社交媒体和 API 数据源管理
9. `09-watch-rules.png`：APT 关注规则、相关性评分和实时测试
10. `10-apt-continuous-tracking.png`：单个 APT 组织月度/年度事件、行为变化与跟踪告警
11. `10-apt-continuous-tracking-custom-range.png`：持续跟踪页的自定义日期范围展开状态，作为工程实现基准

持续跟踪页的自定义日期交互和统计规则见 `CUSTOM-DATE-SPEC.md`。工程开发以 `10-apt-continuous-tracking-custom-range.png` 和该规范共同作为验收依据。

## 视觉规范

- 深色石墨色应用外壳，浅色分析画布。
- 紫色用于主操作和当前选择。
- 青绿色表示已确认/健康，琥珀色表示待确认，红色表示恶意或高风险。
- 主要内容使用连续表面与行分隔，避免卡片堆叠。
- 页面按照 shadcn/ui 的 Sidebar、Command、Tabs、Table、Badge、Button、Resizable、Accordion、Alert、Sheet、Select、Switch 等组件设计。
- 中文正文建议使用 Noto Sans SC，拉丁字符和数字可使用 Inter。

## 核心体验原则

- 每个自动提取结果都能回到原文证据。
- 相似 TTP 不自动等同于攻击者归因。
- Observable 经审核后才能提升为 Indicator。
- 情报流展示相关性原因，而不仅是新闻标题。
- 攻击事件以攻击者、能力、基础设施、受害目标四个钻石模型维度组织。
- 月度和年度趋势按去重后的攻击事件统计，报道数量仅作为独立参考指标。
