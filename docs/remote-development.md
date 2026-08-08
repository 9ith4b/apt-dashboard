# 远程开发环境

## 服务器

- 主机：`server.example.com`
- 用户：`apt-hunter`
- 项目目录：`/opt/apt-hunter`
- Git 裸仓库：`/srv/git/apt-hunter.git`
- Web：`http://server.example.com:8180`
- API 存活检查：`http://server.example.com:8180/api/v1/health/live`

登录密码、数据库密码和对象存储密码不得写入 Git。运行配置保存在远端 `infra/.env`，该文件已被忽略。

## 常用命令

```bash
cd /opt/apt-hunter
git status
git push origin main

cd infra
docker compose ps
docker compose logs --tail=100 api worker web
docker compose up -d --build
docker compose down
```

Node.js 24 安装在用户目录 `~/.local/node-v24`，登录 Shell 通过 `~/.profile` 将其加入 `PATH`。项目的 pnpm 版本由根目录 `package.json` 锁定。

`uv` 安装在 `~/.local/bin`，并管理 Python 3.13。后端虚拟环境位于 `apps/api/.venv`，不替换 Ubuntu 自带的 Python。

## 环境隔离

服务器上原有的 `/opt/legacy-cti-platform` 不属于本项目。APT Hunter 使用独立目录、Compose 项目名、Docker 网络和数据卷，并默认使用 `8180`，避免与原服务的 `8080` 冲突。
