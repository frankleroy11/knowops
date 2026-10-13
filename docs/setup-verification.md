# 环境验证记录

验证日期：2026-10-13（Asia/Shanghai）

- 平台：macOS arm64。
- Conda：knowops，Python 3.11.17。
- PyCharm：已打开本项目；Python Console 实际输出 /opt/anaconda3/envs/knowops/bin/python。
- pip check：No broken requirements found。
- Ruff：All checks passed。
- pytest：1 passed（依赖 TestClient 有一条弃用提示，不影响本次验证）。
- Alembic：0001 (head)，基础知识库表已创建。
- MySQL：临时表插入与读取通过，随后删除临时表。
- Redis：写入、读取通过，随后删除检查 key。
- Milvus：新建临时集合、插入向量、相似度检索命中通过，随后删除临时集合。
- Celery：Redis 入队、Worker 执行、结果返回 pong 通过。
- HTTP /api/v1/health/live：200。
- HTTP /api/v1/health/ready：200，mysql/redis/milvus 均为 ok。

API 在 127.0.0.1:8010 运行，开发 Worker 已启动。后续重开机器时按 README 启动。

业务边界：目前只有工程骨架、基础表和健康接口；前端为预留目录，未接入大模型或 Embedding，未完成业务 RAG 问答。未安装 PyTorch，因此本次未做 MPS 检查。

Docker 首次启动自动恢复已有其他项目容器，初始化较慢。独立服务使用本机缓存镜像，MinIO 版本较旧，仅限开发；后续生产部署需单独升级评估。
