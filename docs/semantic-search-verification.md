# KnowOps 语义检索阶段

2026-10-13，本机 Apple Silicon，Conda knowops。

## 实现

- BGE-M3 本地模型，MPS 优先，1024 维、L2 归一化。
- Milvus 使用 MySQL chunks.id 作为主键，HNSW/COSINE/Strong。
- 集合按模型标识、维度、截断长度和归一化策略派生。
- Alembic 0003：独立 vector_indexes 表，不改解析状态。
- Celery index_document：按版本行锁串行执行、批量 upsert，失败状态可再次投递。
- POST /search 必须指定知识库，返回正文、分数、文件名、位置和页码。
- 回查 MySQL 验证知识库与 indexed 状态。

## 已完成检查

- pip check 无依赖冲突。
- Ruff 通过，pytest 9 passed。
- Alembic current 为 0003，check 无结构差异。
- MySQL/Redis 真实读写、Milvus 临时集合写入检索通过。
- MPS 张量运算与真实 BGE-M3 1024 维编码通过。
- 演示版本 3 的三个切片由真实 Worker 完成索引。

接口使用步骤见 README 的“语义检索（0.3.0）”。

## 当前边界

显式投递索引，未自动串接解析任务；无定时补偿或 processing/租约机制。
索引任务持有版本行锁，适合当前有界本地数据。失败时状态过滤防止未完成版本被展示，
部分失败向量仍可能占据召回名额，因此故障期间命中数量可能不足 top_k。
API 与 Worker 各加载一份模型，首次请求有加载等待和额外内存占用。
当前使用 dense 向量，没有启用 BGE-M3 的 sparse/多向量能力。
尚未实现大模型回答、引用生成、Reranker、鉴权、评估集与生产部署。

## 真实端到端验收

`python scripts/check_retrieval.py` 已通过：真实 HTTP 投递 → Celery Worker →
BGE-M3 → Milvus → MySQL 正文回查。
连续两次索引版本 3，Milvus 中仍为 3 条切片。
查询“在家办公如何连接公司内网？”命中 VPN使用说明.md，首条 COSINE 分数约 0.54366。
另一知识库查询未返回该文档；空白查询返回 422，不存在版本返回 404。
此为小样本功能验收，不代表整体召回率或性能评估。
