# M10 身份、权限、审计与采集安全

更新时间：2026-08-08

## 已交付

- 本地账号使用 Argon2id 哈希，密码原文不写入数据库、日志或前端状态。
- 登录使用随机 HttpOnly 会话 Cookie；支持注销、过期、吊销和账号禁用。
- 登录失败按来源地址与账号限流并触发临时锁定；未知账号仍执行等价密码校验，响应统一为通用错误。
- 所有已认证写请求同时校验同源 `Origin` 与 CSRF Token。
- 服务端强制执行 `viewer`、`analyst`、`admin` 三类角色权限，不依赖前端隐藏按钮。
- 登录、拒绝、CSRF 失败和写操作均记录操作者、请求 ID、对象、结果、地址和时间。
- 管理员页面可以查看账号与最近审计，并可创建、启停、改角色或重置账号密码；最后一个启用管理员不能被停用或降权。
- 返回 CSP、`nosniff`、禁止 iframe、Referrer Policy 和 Permissions Policy 等响应头。
- RSS/Web 抓取限制 MIME、压缩正文大小、解压缩比和文章体积；连接前后都执行地址安全校验，避免 DNS 重新绑定绕过。

## 生产部署

- 地址：`http://server.example.com:8180`
- 生产编排已设置 `APT_HUNTER_AUTH_ENABLED=true`。
- 初始管理员用户名为 `admin`，初始密码只保存在服务器的 `/etc/apt-hunter/admin-initial-password`，文件权限为 `0600`。首次交付后应通过 CLI 重置密码并删除该文件。
- 当前内网部署使用 HTTP，因此 `APT_HUNTER_SESSION_SECURE_COOKIE=false`。切换到 HTTPS 反向代理后必须改为 `true` 并重建 API。
- M10 前数据库备份：`/var/backups/apt-hunter/pre-m10-20260808-121800.dump`，权限 `0600`。
- 数据库迁移版本：`20260808_0009`。

## 权限摘要

| 角色 | 读取 | 研判写操作 | 来源/作业/账号/审计管理 |
| --- | --- | --- | --- |
| viewer | 是 | 否 | 否 |
| analyst | 是 | 是 | 否 |
| admin | 是 | 是 | 是 |

## 验收结果

- 后端：42 项测试通过；Ruff、格式检查和严格 MyPy 通过。
- 前端：16 项交互测试通过；Prettier、ESLint、TypeScript 和生产构建通过。
- 线上：未登录访问 API 返回 401；登录、CSRF 获取、审计读取成功；错误 CSRF 返回 403；4 类安全响应头存在。
- 浏览器：管理员登录和“身份与审计”真实页面加载成功，显示 1 个启用管理员与审计事件，控制台无错误。
- 验收期间没有创建、修改账号或变更真实威胁情报；CaptiveCrunch 材料继续保持 `pending`。

## 下一阶段

自动备份与恢复演练、Prometheus 指标与告警规则、CI/CD、OpenAPI 契约校验、不可变镜像标签和最终全量验收。
