# API 契约

APT Hunter 的 HTTP API 以 FastAPI OpenAPI 3.1 文档作为机器可读契约。当前快照位于 [`openapi.json`](./openapi.json)。

## 更新流程

当路由、请求体或响应模型发生变化时，在仓库根目录执行：

```bash
python apps/api/scripts/export_openapi.py
git diff -- docs/openapi.json
```

CI 会执行以下命令并拒绝未同步的契约变更：

```bash
python apps/api/scripts/export_openapi.py --check
```

生产环境默认关闭交互式 Swagger UI，避免额外暴露接口枚举入口；经过认证的开发环境仍可使用 `/docs`。健康检查位于 `/api/v1/health/*`，Prometheus 指标位于仅供内部 Compose 网络抓取的 `/metrics`。

兼容性约束：

- 新增可选字段或新端点属于向后兼容变更。
- 删除字段、收紧枚举或改变字段含义必须提升主版本并提供迁移说明。
- 所有写请求在生产环境要求已认证会话、同源 `Origin` 和 `X-CSRF-Token`。
- 客户端必须处理 401、403、409、422、429 和 5xx，而不是只依赖成功响应模型。
