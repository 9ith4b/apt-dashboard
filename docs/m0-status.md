# M0 工程基线验收

## 已完成

- pnpm workspace、Vite、React、TypeScript、Tailwind CSS 与 shadcn/ui 前端基线。
- 情报流首个可交互垂直切片，以及事件、攻击者、Campaign、IOC、关注规则、数据源、待审核路由骨架。
- FastAPI 健康检查、SQLAlchemy 核心模型、Alembic 初始迁移和 Celery Worker/Beat 基线。
- PostgreSQL、Redis、MinIO、API、Worker、Beat、Web 的 Docker Compose 编排。
- GitHub Actions 前端、后端与 Compose 静态校验流水线。

## 原型对照记录

对照基准：`outputs/apt-hunter-prototype/01-intelligence-feed.png`

实现截图：`outputs/apt-hunter-m0-preview.png`
原生尺寸：1487 × 1058。

| 对照项 | 结果 |
| --- | --- |
| 深色石墨背景、紫色主色与语义状态色 | 一致 |
| 左侧导航、顶部工具栏、统计带、主列表、右侧速览三栏结构 | 一致 |
| 六条情报、默认选中态、标签与来源信息层级 | 一致 |
| Lazarus 虚假面试案例与威胁钻石四要素 | 一致 |
| 固定底部“打开事件图谱”主操作 | 一致 |
| 字体密度与边距 | 实现略紧凑，保留以提升 1366px 屏幕可用性 |
| 全部来源筛选、通知数字、来源置信度明细 | 推迟到 M1 数据接入阶段 |

## 浏览器验收

- 桌面视口 1487 × 1058：无水平溢出，6 条情报完整渲染。
- 窄屏视口 768 × 900：无水平溢出，事件速览按断点隐藏。
- 选择 APT28 后，右侧速览的摘要同步更新。
- “事件图谱”导航进入 `/events`，返回“情报流”进入 `/feed`。
- 页面标题为 `APT Hunter`，中文语言元数据已配置。

## 下一阶段入口

M1 从 RSS 单源闭环开始：创建数据源、定时拉取、文章去重、正文抽取、APT 相关性判定、候选事件生成、人工审核入库。社交媒体适配器在该闭环稳定后复用同一规范化接口接入。
