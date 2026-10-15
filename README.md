# KnowOps 企业知识库问答平台

当前阶段：Vue 演示界面、自动文档入库与带引用问答（0.5.0）。支持创建知识库、上传 TXT / Markdown / 文本 PDF、异步解析、BGE-M3 向量化、Milvus 索引、限定知识库的语义检索与失败重试。已接入 Qwen 单轮问答与来源引用；鉴权、版本更新与发布尚未实现。

## 开发环境

- Apple Silicon / Python 3.11，Conda 环境 `knowops`
- 解释器：`/opt/anaconda3/envs/knowops/bin/python`
- PyCharm 项目解释器已设置为上述路径；运行 `run.py` 或选择 `KnowOps API` 配置。
- 已安装依赖见 requirements.txt，实际版本快照见 requirements.lock.txt。
- 已安装 PyTorch、Sentence Transformers，并验证 BGE-M3 在 MPS 上生成 1024 维向量；LangChain 尚未接入。

## 目录

```text
app/
  core/                 配置
  db/                   SQLAlchemy 连接与会话
  modules/
    auth/               用户与权限（待实现）
    knowledge/          知识库、文档、版本、切片数据模型与接口
    ingestion/          文本解析、按字符切分、PDF 页码保留
    retrieval/          语义检索与异步索引（已实现）
    chat/               会话与问答（待实现）
    feedback/           反馈与追踪（待实现）
    health/             健康检查（已实现）
  adapters/             Embedding、Milvus 已实现；LLM、Reranker、存储扩展预留
  workers/              Celery 解析、索引与 ping 任务
migrations/             Alembic 迁移
frontend/               Vue 前端预留
storage/                原始文件预留
scripts/                服务读写与向量检索检查
tests/                 基础接口测试
evals/                 评估预留
```

## 启动

在项目根目录的终端执行：

```bash
conda activate knowops
docker compose up -d
python -m alembic upgrade head
python run.py
```

接口文档：http://127.0.0.1:8010/docs

- 存活检查：`GET /api/v1/health/live`
- MySQL、Redis、Milvus 就绪检查：`GET /api/v1/health/ready`，失败返回 503。

在另一个终端启动 Worker（macOS 开发使用 solo，代码更改后需重启 Worker）：

```bash
conda activate knowops
celery -A app.workers.celery_app:celery_app worker --pool=solo --loglevel=info
```

验证：

```bash
python -m pip check
python -m pytest -q
ruff check .
python scripts/check_services.py
python scripts/check_retrieval.py
```

## 服务地址

| 服务 | macOS 访问地址 | Compose 网络内地址 |
|---|---|---|
| MySQL | 127.0.0.1:13306 | mysql:3306 |
| Redis | 127.0.0.1:16379 | redis:6379 |
| Milvus | 127.0.0.1:19540 | milvus:19530 |
| Milvus 健康端口 | 127.0.0.1:19091 | milvus:9091 |

MySQL 和 MinIO 开发密码为随机生成，保存在本地 `.env`，请勿提交。
配置针对 macOS 运行 API/Worker。若将它们放入容器，需要切换为网络内地址。
服务仅绑定本机回环地址；Compose 是开发配置，不能直接作为生产部署。
MinIO 当前仅作为 Milvus 的底层依赖，业务原文件暂用 storage/。
本机已有的课程服务不会被本项目修改；本项目容器和卷使用 knowops 前缀。

停止基础服务（保留数据卷）：

```bash
docker compose stop
```

## 后续开发顺序

1. 文档、版本和切片的数据模型与迁移。
2. Markdown / TXT / 文本 PDF 上传、解析与异步任务。
3. Embedding、Milvus 检索、大模型调用、带引用问答。
4. 权限、版本发布、幂等重试和补偿机制。
5. 混合召回、重排序、评估集与实验报告。

## 文档入库操作

打开 /docs，按以下顺序调试：

1. `POST /api/v1/knowledge-bases`：例如 `{"name":"IT运维知识库","description":"VPN与账号使用说明"}`。
2. `POST /api/v1/knowledge-bases/{kb_id}/documents`：选择文件上传，返回 document_id、version_id、queued。
3. `GET /api/v1/documents/{document_id}`：查询 pending / parsed / failed 状态以及切片数。
4. `GET /api/v1/document-versions/{version_id}/chunks`：查看正文与 PDF 页码，支持 limit / offset。
5. `POST /api/v1/document-versions/{version_id}/retry`：重新投递待处理或失败版本。

每次上传创建新文档及版本 1，尚未提供更新同一文档的接口；SHA-256 目前用于记录内容指纹，不代表跨文档去重。
单文件上限 10 MiB，文本要求 UTF-8。扫描或加密 PDF 不支持；解析失败会显示 failed。
当前以 800 字符窗口、100 字符重叠切分，PDF 按页切分，尚未做语义切分或 token 限制。
parsed 仅代表文本已解析、切片已写入 MySQL，不代表已经向量化或可问答。
任务重复执行会锁定同一版本，并跳过 parsed 版本；数据库瞬时连接错误最多自动重试 3 次。
入队失败时保留 pending 记录并返回 queued=false，可通过 retry 接口补发。
当前未实现定时补偿扫描。所有接口用于本机开发，鉴权尚未接入。

实际链路检查（需要 API、Worker 和基础服务运行，会保留命名的演示知识库）：

```bash
python scripts/check_ingestion.py
```

### 语义检索（0.3.0）

在 `knowops` 环境安装 requirements 并执行 `python -m alembic upgrade head`。
修改任务代码后重启 Celery Worker。BGE-M3 首次加载下载权重，Apple Silicon 优先 MPS，
无 MPS 时使用 CPU；使用 1024 维、L2 归一化、COSINE 相似度。

在 `/docs` 中操作：

1. 上传文档并等待解析状态 `parsed`。
2. `POST /api/v1/document-versions/{version_id}/index` 投递索引任务。
3. `GET /api/v1/document-versions/{version_id}/index` 查看 `indexed` 或 `failed`。
4. `POST /api/v1/search`，请求示例：

```json
{"query":"在家办公如何连接公司内网？","knowledge_base_id":2,"top_k":3}
```

返回正文、文档名、版本、切片位置、PDF 页码与相似度。必须指定知识库。
索引失败可再次调用同一个 POST；切片 ID 为 Milvus 主键，重复执行不会追加重复记录。
模型标识、维度、截断长度及归一化策略共同决定集合名。
解析状态与索引状态独立；检索只返回 MySQL 中标记为 indexed 的版本。
索引任务执行期间状态保持之前值，尚未增加 processing 状态或定时补偿。
从 0.5.0 起解析后自动投递索引，仍可手动重新索引。尚无鉴权、重排或大模型回答。
有界本地文档索引持有版本行锁，长任务需后续改为租约；失败产生的部分向量通过
MySQL indexed 状态过滤，重新索引覆盖恢复。模型权重升级应使用新的模型标识/集合。

`python scripts/check_retrieval.py` 对既有演示文档 3 执行真实索引与检索验证，保留索引数据。

### 带来源引用的问答（0.4.0）

本地 `.env` 配置 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`。
百炼中国内地服务示例：`LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`，
`LLM_MODEL=qwen-plus`。其他地域请使用对应 endpoint。密钥不得提交到 Git。
修改配置后重启 API，或在开发模式下触发代码重载。

`POST /api/v1/chat/ask`：

```json
{"question":"在家办公如何连接公司内网？","knowledge_base_id":2,"top_k":3}
```

返回 `answer`、`answerable` 和 `citations`（真实切片正文、文件名、页码及编号）。
后端校验模型返回的引用编号并映射到检索切片；无资料、模型拒答、引用编号不存在时返回资料不足。
这能校验引用确实来自检索结果，不能保证每句话都获得正确语义支持，仍需评估回答忠实度。
资料和用户输入均作为不可信数据处理，系统提示约束模型只依据资料回答；不能宣称完全阻止提示注入。
当前为单轮、非流式问答，不保存会话；LLM 超时/服务错误返回 503，响应结构错误返回 502。
Qwen API 会接收问题及所选切片正文，真实私密资料需先明确数据使用要求。

### Vue 演示界面（0.5.0）

在 frontend 目录执行 `npm ci`、`npm run build`，然后启动（或重启）API 与 Worker。
打开 http://127.0.0.1:8010/ui/ ，在同一地址完成知识库创建、文档上传、状态查看、失败重试和带引用问答。
解析完成后 Worker 自动投递索引任务；任务投递失败仍可在界面点击“重试索引”。
解析与索引状态分开显示，当前页每 5 秒自动刷新；API 返回最新版本和切片数量。
文档列表每页 20 条，知识库按分页接口完整加载。
前端仅通过同源 /api/v1 访问后端，无密钥；不启用跨域通配。
目前对话仅保存在页面内存，刷新/切换知识库会清空，不支持历史会话或流式输出。

前端开发热更新：在 frontend 执行 `npm run dev`，访问 http://127.0.0.1:5173/ui/ 。

### 固定评估集

当前数据集为**星桥科技合成语料**：3 个知识库、126 份语料（含 6 份 PDF 附录）、452 个切片、168 道固定题
（含 18 道跨库隔离题）。语料为合成内容，不对应任何真实企业，指标不能作为真实企业准确率依据。

```bash
python evals/tools/build_questions.py     # 校验 168 条标注并生成 questions.json / manifest.json
python scripts/evaluate_v2.py             # 完整评估：入库 → 索引 → 检索 + 问答
python scripts/evaluate_v2.py --skip-chat # 只评检索，不调用大模型
python scripts/evaluate_v2.py --reuse --top-k 5   # 复用已入库数据做参数对照
```

结果写入 `evals/runs/<北京时间>/`：`metadata.json`（语料哈希、模型、索引耗时、PDF 页码）、
`results.json`、`report.md`（含逐题人工复核栏）。

指标包含文档级 Recall@k、**切片级** Recall@k、MRR、nDCG、拒答准确率、引用来源匹配，
并按难度（easy / paraphrase / numeric / multi_source）与 dev / test 分组。
关键词筛查仅作线索，**不是**回答正确率。

数据集构成、标注校验规则、真实评估结果与已知局限见 `docs/dataset-verification.md`；
指标口径与局限见 `evals/README.md`。旧版 30 题数据集与基线 run 保留在 `evals/legacy/`。
`/chat/ask` 额外返回 `timings_ms`，便于区分检索与生成耗时。

### 可选重排序（实验）

`/search` 和 `/chat/ask` 默认 `rerank=false`，现有页面继续使用原检索方案。
请求中设置 `rerank=true, candidate_k=10, top_k=3`，先召回 10 条再由本地
BAAI/bge-reranker-base 重排返回 3 条。`max_per_document=2` 可限制同文档切片数量（软限制，
不足 3 条时以剩余候选补齐），默认 0 不限制。候选数必须大于等于返回数。
Milvus COSINE `score` 保留；重排分数单独返回 `rerank_score`，两者不能直接比较。
模型懒加载，Apple Silicon 优先 MPS；首次请求包含模型加载耗时，模型不可用时返回 503。
重排输入最多 512 token，超出部分会截断，需通过评估检查长切片的信息损失。

运行 `python scripts/evaluate_reranker.py`，只在 dev 集执行检索对照，不调用 Qwen，复用
synthetic-v1 三个知识库。同一批候选分别取 dense 前三、重排前三、带文档软限制的重排前三。
结果位于 `evals/reranker_runs/`。记录独立重排耗时与共享召回耗时，不把模型下载与初始化计入稳态统计。

评估现已支持等价证据补充标注（`evals/evidence_annotations.json`）。原指定来源指标与
补充标注指标分别保留，修改理由和候选重评分结果见 `docs/evidence-annotation-review.md`。
生产问答仍默认使用 dense 检索；新口径下重排的开发集收益尚待新的盲测与生成质量验证。

### 新题留出验证

18道新题、36次真实Qwen调用的前瞻冻结测试已完成。普通检索的严格完整证据覆盖为9/12，
重排序为8/12；重排序增加约621ms中位耗时，因此保持默认关闭。
这是一组助手构建的合成语料小样本，不是独立人工正确率。详见 [留出测试报告](docs/holdout-evaluation.md)。

### 逐事实引用校验（开发分支）

`fix/citation-completeness` 为每个回答事实增加可核对的原文摘录，后端验证出处并组装引用。
实际回归暴露了额外拒答，暂不合并main。实现边界和对照见 [逐事实引用报告](docs/citation-completeness.md)。

### 统一问答

页面默认进入“统一问答”，从当前空间全部知识库检索，引用标明所属知识库。
选择左侧单个知识库可限定检索并管理该库文档。API通过显式`scope=all`启用，
原来的`knowledge_base_id`请求和单库隔离行为不变。见 [统一问答说明](docs/unified-chat.md)。

### 查看向量数据库

可选管理界面：运行 `docker compose --profile admin up -d attu` 后打开
[Attu](http://127.0.0.1:8000/)，连接地址保持 `milvus:19530`，数据库为 `default`。
它可查看向量集合、索引及记录。宿主机的19540端口是Milvus接口，没有网页首页。
详见 [Attu使用说明](docs/milvus-attu.md)。

### 可选补充同文档资料（开发分支）

草稿PR #1新增相邻片段补全：前端勾选“补充同文档资料”或请求`expand_context=true`，
最多提供8片同文档上下文，默认关闭。已实测修复合同审批时限和耗材特例的缺片问题，
但仍有模型误拒答且生成耗时增加，尚未合并main。见 [实现与回归报告](docs/context-completion.md)。
