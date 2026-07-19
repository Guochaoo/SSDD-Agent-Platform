# Release 运行手册

本手册对应仓库中的 `docker-compose.yml`、`docker-compose.prod.yml`、`.env.production.example` 和 `scripts/`。生产部署不应使用开发 Compose 中的默认账号或端口暴露。

## 生产启动

1. 复制 `.env.production.example` 为 `.env.production`，替换全部 `REPLACE_...` 占位符，并设置实际域名的 `ALLOWED_ORIGINS`。生产 Compose 会把 backend 的 `DB_NAME`、`DB_USER`、`DB_PASSWORD` 显式绑定到 `POSTGRES_*`，因此这三组值不可能因人工填写不一致而导致连接失败。
2. 在仓库根目录运行：

   ```powershell
   docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up -d --build
   ```

3. 后端容器会先执行 `alembic upgrade head`，再启动 Uvicorn。前端仅暴露 `${APP_PORT:-8080}`；PostgreSQL、Redis、MinIO 不对外暴露。

## 发布验收

```powershell
Invoke-RestMethod http://127.0.0.1:8080/api/health/detail
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml ps
```

`/api/health/detail` 必须同时显示 PostgreSQL、Redis、MinIO 为 `healthy`。Compose 同时检查 backend 的该端点和 frontend 的 Nginx 响应；frontend 会等待 backend 通过健康检查后才启动。生产模式（`DEBUG=false`）会拒绝示例密钥、localhost/通配符 CORS，并禁用 `/docs`、`/redoc`。

资源清理补偿由 backend 生命周期任务调度，并以 Redis 锁保证多 worker 中同一时刻只有一个执行者；Redis 不可用时该轮会安全跳过，待 Redis 恢复后重试，不会退化为多个进程并发删除。

## 备份

备份会导出 PostgreSQL、镜像 `ssdd-images` MinIO bucket 和 `runs/`，不会修改服务数据。

```powershell
$env:POSTGRES_USER = '...'
$env:POSTGRES_DB = '...'
$env:MINIO_ACCESS_KEY = '...'
$env:MINIO_SECRET_KEY = '...'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup.ps1 -BackupDir D:\ssdd-backups\release-001 -ComposeFiles docker-compose.yml,docker-compose.prod.yml -EnvFile .env.production
```

备份目录中的 `manifest.json` 是恢复前必须检查的清单。仓库内已完成一次真实备份演练；MinIO 对象和 PostgreSQL dump 均已成功生成。

## 恢复与回滚

恢复会覆盖当前数据库与 bucket，必须显式确认：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\restore.ps1 -BackupDir D:\ssdd-backups\release-001 -Confirm -ComposeFiles docker-compose.yml,docker-compose.prod.yml -EnvFile .env.production
```

生产 backend 的 `/app/runs` 使用 `backend_runs` 命名卷；备份脚本通过 Compose 定位 backend 容器并复制该目录，恢复时会先清空该卷中的旧训练输出，再恢复快照。恢复后重启 backend，并再次检查 `/api/health/detail` 与 `alembic current`。应用版本回滚应先切换到已验证的 Git 提交，再执行同一 Compose 命令；不要使用 `docker compose down -v`，以免删除持久卷。

## 当前验证边界

- 前端生产镜像和 Nginx 配置已在 Docker 中实际构建并通过 `nginx -t`。
- 后端镜像已验证 Dockerfile 语法与构建入口；本机 Docker 构建曾被 Debian 软件源 502 中断，后续重试还出现 Docker content-store 的 `size validation` 失败，均尚未进入项目代码或 Python 依赖安装。修复 Docker 镜像拉取/内容存储后应重新运行 `docker build -t ssdd-backend:verification backend`。
