# 安全与隐私策略

## 漏洞报告

请使用 GitHub 的 Private Vulnerability Reporting 提交安全问题，不要在公开 Issue 中粘贴漏洞细节、访问令牌、日志、情报原文或生产环境截图。

## 仓库中禁止出现的内容

- 真实的 `.env`、API Key、Cookie、会话令牌、私钥、证书私钥和数据库连接口令。
- 数据库、对象存储、备份、日志、HAR/PCAP、生产截图和未经脱敏的威胁情报样本。
- 内网 IP、真实服务器名、SSH 用户名、个人主目录、开发者姓名或邮箱等部署身份信息。
- AI 提供商、X、Telegram 等外部服务的真实凭据。

仓库只保留 `.env.example`，其中所有值必须是明显不可用的占位符。真实配置应由部署环境、GitHub Actions Secrets 或受控的密码管理器注入。服务器上的 `infra/.env` 必须保持 `0600` 权限。

## 发布前检查

```bash
python scripts/privacy_check.py
git status --short --ignored
git log --all --format='%an <%ae>' | sort -u
```

确认仅发布已经审计的分支和标签，禁止直接执行未经核对的 `git push --all` 或 `git push --mirror`。本仓库的 CI 会检查当前提交中的高风险凭据格式、私钥、内网部署地址和个人主目录。

如果凭据曾进入 Git 历史，仅删除当前文件并不足够：先在提供商处吊销并轮换凭据，再重写所有将公开的分支和标签，最后重新执行隐私检查。
