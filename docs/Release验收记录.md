# Release 验收记录

本记录仅列出已在本地工作区实际执行的结果；外部服务、生产密钥和真实训练数据未准备时不以模拟结果替代。

## 2026-07-19

| 项目 | 实际结果 | 证据 |
| --- | --- | --- |
| 后端回归 | 141 passed，4 个 Pydantic 兼容性警告 | `python -m pytest backend/tests -q` |
| 前端回归 | 13 files / 41 tests passed | `npm.cmd run test:run`（`frontend/`） |
| 前端构建 | 通过；仍有 3 个大于 500 kB 的现有分包告警 | `npm.cmd run build`（`frontend/`） |
| 生产 Compose 配置 | 合并开发与生产 Compose 后，五个服务的配置校验通过 | 使用无真实密钥的临时 `.env.production` 执行 `docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml config --quiet`；该临时文件已移除 |
| 基础设施健康 | PostgreSQL、Redis、MinIO 均为 healthy | Docker Compose 状态及 `http://127.0.0.1:8002/api/health/detail` |
| 真实单图推理 | 内置默认模型完成 `hero.png` CPU 推理；131.76 ms、0 个目标，并生成标注产物 | `DetectionService._detect_file_sync()`，不创建业务任务、不作为模型质量指标 |
| 最小真实训练闭环 | 临时用户上传两张不同图片的数据集后，CPU 完成 10/10 epoch；持久化 10 条指标，`results.csv` 下载返回 200（3,707 B）；任务、数据集、用户和输出目录均已删除 | 隔离后端连接 Docker PostgreSQL、Redis、MinIO；当前 venv 的 PyTorch 不支持 CUDA，故将缺失设备参数的默认值统一为 `cpu` |
| 模型供应商 | `/api/agent/models` 实际返回 229 个模型；当前 `qwen-plus` 直连、文本 SSE 与带图工具调用均成功 | 隔离后端 `http://127.0.0.1:8003`；测试用户、会话、上传图和标注产物均已清理 |
| 真实 Embedding | `qwen3.7-text-embedding` 实际返回非零 768 维向量，与 pgvector 列一致 | 进程级 `NO_PROXY=dashscope.aliyuncs.com` 下调用，不写入知识库 |
| 真实 Agent SSE | `qwen-plus` 完成通用 Agent 切换、35 个文本分片、`message_end` 与 `DONE`；带图检测请求完成检测 Agent 切换、1 次工具开始/结果和 24 个文本分片，均无错误 | 应用启动自动注入 DashScope 进程级代理绕过；临时会话与用户均已删除 |
| 真实 RAG 闭环 | 临时 TXT 文档完成 MinIO 上传、解析、1 个分块、768 维入库与 1 条检索命中；删除同步完成 | 隔离后端实际 API；临时用户、文档、分块和对象均已删除 |
| Agent 检测工具闭环 | 通过：带图请求实际调用 `detect_single_image`，生成 success 工具卡并持久化；授权 artifact 读取返回 200 / `image/jpeg` | 使用现有内置权重对 32×32 测试图推理得到 0 个目标，不作为模型质量指标；临时会话、用户与上传文件均已清理 |
| 实际库迁移 | 当前版本和唯一 head 均为 `b2c3d4e5f6a7` | `alembic current`、`alembic heads`，连接 Compose PostgreSQL |
| 空库迁移演练 | 临时 `ssdd_release_verify` 完成 `upgrade head -> downgrade base -> upgrade head`，后已删除 | 真实 PostgreSQL + pgvector 临时库 |
| 备份 | PostgreSQL dump、MinIO bucket 与 `runs/` 的备份脚本已实际成功运行；最新演练生成 manifest 和 335 个 MinIO 对象 | `scripts/backup.ps1`；基础 Compose 本地回退和临时 backend 容器 `/app/runs` 分支均已验证，生产 Compose 使用 `backend_runs` 卷 |

## 未替代为“已验收”的项

- 后端 Docker 镜像：已清理 2.315 GB 可再生成 Build 缓存并重启 Docker Desktop；已移除镜像源列表中的占位地址，基础服务恢复 healthy，但 `python:3.10-slim-bookworm` 拉取仍被其余第三方镜像源返回非 JSON referrers 索引阻断，未生成 `ssdd-backend:verification` 镜像。只读探测确认部分源返回 `text/html`，其余部分存在 TLS、超时或限流问题；将列表收敛为两个 JSON 响应源会触发 Docker Desktop 4.80 后端空指针崩溃，已立即回退至可启动配置。
- 真实 LLM 对话、SSE 工具调用、文档入库与单条 RAG 检索已验证；检索质量评估、多工具路由、供应商故障和实际业务数据仍需要受控数据集与验收样本。
- 模型供应商此前曾返回 `Arrearage`；当前 `qwen-plus` 的文本与带图 Agent 闭环已复测成功。仍应在正式验收中记录所用账户、模型和时间，并以真实业务样本复核多 Agent 路由。
- 真实训练闭环已用最小临时数据集验证；GPU 性能、模型质量、长视频和多用户摄像头并发仍需要可发布的模型权重、真实数据集与受控硬件条件。当前 venv 的 PyTorch 未启用 CUDA。
- 完整生产 Compose：需要由部署人员创建真实 `.env.production`；示例文件不含可用密钥，不能用于启动生产服务。

上述限制不影响已列出的单元、组件、构建、基础设施健康和迁移演练结果。
