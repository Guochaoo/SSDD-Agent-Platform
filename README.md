# SSDD Agent Platform

YOLOv11 钢铁表面缺陷检测智能体平台，包含 Vue 3 前端、FastAPI 后端、PostgreSQL/pgvector、Redis 和 MinIO。

## 一键启动

要求：Docker Desktop（或 Linux Docker Engine）和 Docker Compose v2。

开发/验收环境在仓库根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Build
```

启动后访问：

- 前端：http://127.0.0.1:8080
- 后端健康检查：http://127.0.0.1:8000/api/health/detail
- 前端代理健康检查：http://127.0.0.1:8080/api/health/detail

查看日志或停止：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Logs
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\stop.ps1
```

Linux/macOS 可直接使用同一套 Compose：

```bash
docker compose -f docker-compose.yml up -d --build
```

Compose 会按顺序启动基础设施、执行 Alembic 数据库迁移、启动后端，再启动前端。数据写入 Docker volumes，普通 `down` 不会删除数据；除非明确确认，不要使用 `down -v`。

## 生产部署

1. 复制环境模板并填写真实值：

   ```powershell
   Copy-Item .env.production.example .env.production
   notepad .env.production
   ```

   必须替换所有 `REPLACE_*`，`DEBUG=false`，并将 `ALLOWED_ORIGINS` 设置为实际域名。`.env.production` 只放在部署主机，不提交 Git、不放进镜像和发布包。

2. 在仓库根目录一键启动生产 Compose：

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\start.ps1 -Production -Build
   ```

   Linux/macOS：

   ```bash
   docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

生产模式只对外暴露前端端口（默认 8080）；PostgreSQL、Redis、MinIO 和后端通过 Compose 内网通信。云服务器防火墙只开放 80/443（或实际前端端口）及受限的 SSH 端口，不开放 5432、6379、9000、9001、8000。

## 发布包

发布包只从 Git 已跟踪文件生成，不包含私密配置、日志、缓存、数据集、模型权重、运行输出、虚拟环境和 `node_modules`：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\package-release.ps1
```

默认生成 `dist\ssdd-agent-platform-deployment.zip`。部署主机解压后，单独创建 `.env.production`，再执行生产启动命令。

## 验证与运维

```powershell
docker compose ps
Invoke-RestMethod http://127.0.0.1:8080/api/health/detail
docker compose exec backend alembic current
```

备份与恢复请使用 `scripts/backup.ps1` 和 `scripts/restore.ps1`，先核对目标 Compose、环境文件和备份清单。模型权重、数据集和 MinIO/数据库业务数据属于运行时资产，不随代码发布包分发，应通过受控的备份或制品存储单独迁移。

更多验收、部署和回滚说明见 [`docs/Release运行手册.md`](docs/Release运行手册.md)。开发约定见 [`项目规范.md`](项目规范.md)。

## 当前验证边界

本分支会验证 Compose 配置、打包排除规则和前端/后端静态检查。完整后端测试仍取决于本机 Python 依赖和 Docker 服务是否可用；未在真实云服务器上部署成功前，不将本地构建结果表述为生产验收通过。
