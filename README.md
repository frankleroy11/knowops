# KnowOps 企业知识库问答平台

KnowOps 将企业文档上传、异步解析、向量检索、审核发布和带引用问答连成一条可验证的 RAG 流程。后端使用 FastAPI、MySQL、Redis、Celery、Milvus；本地 BGE-M3 负责嵌入，Qwen API 负责回答，LangChain Core 编排提示词、模型调用和严格 JSON 解析。Vue 提供用户工作台与管理员控制台。

当前功能：FAQ 优先匹配与 Redis 问答缓存、统一/单库问答、按事实校验原文引用、多租户与知识库成员权限、密码/Token 登录、可选 OIDC/TOTP、文档版本审核与切换、失败定位与重试、知识库改名/删除、文档删除、审计和答案反馈、系统状态页。答案为单轮 SSE 流式传输（实时生成进度，完整校验后返回正文）；引用逐字匹配不等于语义正确，仍保留已知误拒答及评测失败案例。

当前能力、未完成项及最新验证见 [功能状态清单](docs/feature-status.md)。问答页面支持选择 1–8 段召回资料，默认 3 段。

生成链路详见 [LangChain 接入说明](docs/langchain-generation.md)；检索权限、版本审核与引用校验仍由业务层执行。

## 快速启动（本机开发）

Python 3.11；Apple Silicon 使用 MPS，其他设备回退 CPU。API/Worker 在宿主机运行，Docker 运行基础服务。

```bash
conda activate knowops
python -m pip install -r requirements.txt
# 首次安装：复制 .env.example 为 .env，再填入随机数据库密码、模型路径和 Qwen 配置。
docker compose up -d
python -m alembic upgrade head
npm --prefix frontend ci
npm --prefix frontend run build
# 首次启用认证前创建平台管理员，凭据仅写入被 Git 忽略的 0600 本地文件。
PYTHONPATH=. python scripts/bootstrap_admin.py
# 在 .env 设置 AUTH_MODE=enforced，然后启动 API。
python run.py
```

另一个终端启动 Worker；改任务代码后必须重启 Worker：

```bash
conda activate knowops
celery -A app.workers.celery_app:celery_app worker --pool=solo --loglevel=info --hostname=knowops@%h
```

打开 [工作台](http://127.0.0.1:8010/ui/) 或 [接口文档](http://127.0.0.1:8010/docs)。首次账号在 `.tmp/local-admin-credentials.json`，请在本机读取并在登录后设置自己的密码。不要提交或对外分享该文件。已有平台管理员时 bootstrap 不改凭据。

`AUTH_MODE=off` 是明确的本地免鉴权模式，所有调用均视为平台管理员。正常使用推荐 `enforced`；本次已在本机开启。修改 `.env` 后重启 API/Worker，不能依赖前端刷新或 `.env` 自动重载。

## 开放注册与多用户演示

本机已开放注册：登录页点击“注册账号”，成功后获得独立演示空间，可管理自己的知识库和成员。不会自动进入原有企业空间。平台管理员可统一搜索与管理账号，租户管理员仅管理自己空间。邮箱验证和邮件发送未接入；忘记密码请联系管理员。

详见 [注册、登录和多用户管理](docs/public-registration-users.md)。`PUBLIC_REGISTRATION_ENABLED=false` 可关闭公开注册；仅在强制登录模式生效。

## 用户流程与角色

1. 管理员创建租户、账号、知识库，分配成员权限。
2. 编辑者上传 TXT、Markdown 或文本 PDF；Celery 解析并自动向量化。
3. 启用审核的知识库，由其他有写权限的成员审核；管理员可审核自己的提交。
4. 用户在统一窗口提问，检索仅限其有权读取的已发布、审核通过、解析/索引成功版本。
5. 查看引用并提交答案反馈。管理控制台可定位失败、重试失败阶段、切换有效版本或删除资料。

平台管理员可跨租户管理并查看系统状态；租户管理员只管理本租户；编辑者需要知识库写权限；只读用户只能阅读和提问。普通用户看不到控制台入口，后端也执行权限检查。

## 项目结构

```text
app/core/                  配置
app/db/                    SQLAlchemy 与依赖
app/modules/auth/          认证、账号安全与授权
app/modules/tenant/        租户管理
app/modules/knowledge/     文档、版本、审核与删除
app/modules/ingestion/     文本/PDF 解析与切分
app/modules/retrieval/     BGE-M3/Milvus、可选重排和相邻上下文
app/modules/chat/          Qwen 问答与逐事实引用校验
app/modules/feedback/      答案反馈
app/modules/audit/          租户审计
app/modules/system/        平台系统状态
app/adapters/              模型、向量库、文件存储
app/workers/               Celery 解析/索引任务
frontend/                  Vue 工作台和管理控制台
migrations/                Alembic 迁移
storage/                   本地原始上传文件（忽略入 Git）
evals/                     合成数据集、实验结果和失败案例
scripts/                   真实服务验收与运维工具
```

## 服务地址

| 服务 | 宿主机 | Compose 网络内 |
|---|---|---|
| API | 127.0.0.1:8010 | 当前不在容器中 |
| MySQL | 127.0.0.1:13306 | mysql:3306 |
| Redis | 127.0.0.1:16379 | redis:6379 |
| Milvus | 127.0.0.1:19540 | milvus:19530 |
| Milvus 健康端口 | 127.0.0.1:19091 | milvus:9091 |
| 可选 Attu | 127.0.0.1:8000 | 连接 milvus:19530 |

`docker compose --profile admin up -d attu` 启用向量管理界面。Milvus 的 19540 端口没有网页首页。MinIO 是 Milvus 底层依赖，业务原文件仍在 `storage/`。

## 验证

```bash
ruff check .
python -m pytest -q
node --test frontend/test/*.test.mjs
npm --prefix frontend run build
# 需强制认证 API、Worker、模型缓存及基础服务，会调用真实 Qwen。
PYTHONPATH=. python scripts/check_release_flow.py --base-url http://127.0.0.1:8010/api/v1
```

真实回归使用临时租户、账号和合成文档；验证后清理本次数据并核对所有表记录数、逻辑向量数、存储文件集合。不要与业务写入并行运行。开发回归不是盲测，关键词与引用检查不是人工答案正确率。

## 边界与运行文档

- 单文件 10 MiB，文本须 UTF-8；扫描/加密 PDF 需要外部 OCR/解密，不会靠重试自动修复。
- 默认按固定字符窗口切分，可选 `CHUNK_STRATEGY=structure` 优先结构边界；每个版本记录切分策略，旧文档不会自动重切。见 [切分对照与使用说明](docs/structure-aware-chunking.md)。SHA-256 是指纹，不是跨文档去重。
- MySQL 是正文、权限与版本状态权威；Milvus 为可重建检索副本。解析完成不等于可问答。
- 删除跨 MySQL/Milvus/文件系统无分布式事务；部分清理失败可重试，磁盘遗留由 GC 处理。
- 没有自动修复卡住的索引租约、流式多轮对话、生产高可用或已验证的生产容量。
- OIDC/TOTP 代码与测试保留；真实生产 IdP、邮件发送通道和公网 TLS 未在本机交付中验证。
- Qwen 接收问题和所选切片正文；本次真实评测仅使用合成资料。

详见 [部署、备份恢复和故障排查](docs/operations-runbook.md)、[文档管理](docs/document-operations.md)、[系统状态](docs/system-status.md)、[本次交付验收](docs/release-acceptance-20261015.md)。旧的阶段报告保留为历史证据，以这些当前文档及真实代码为准。

## 本地演示明文密码

在 `.env` 设置 `PASSWORD_STORAGE=plaintext` 并重启 API 后，新建／重设密码在 `users.password_hash` 中按 `plaintext$原密码` 保存。前缀只是格式标记，没有加密。密码历史也可能保存这种格式。已有 scrypt 摘要无法还原，账号在成功完成密码及二次验证登录后转换。切回 `scrypt` 后，成功登录或重设密码会转换回摘要；旧密码历史不会自动重写。

此模式会让数据库和备份直接暴露密码，演示请使用独立测试密码。API 不返回密码字段，令牌仍保存摘要。仓库默认配置仍是 `scrypt`。

## 最新演示交付

- [2026-10-16 验收报告与演示步骤](docs/release-acceptance-20261016.md)
- [当前架构与数据流](docs/architecture.md)
- [后端中文阅读指南](docs/backend-code-reading-guide.md)

本轮真实 Qwen 合成开发题启发式通过 4/5，保留报销凭证误拒答；不作为独立盲测正确率。

## FAQ 优先问答

管理员可在“管理控制台 → 高频问答”维护带原文证据的标准答案；精确／语义命中直接返回，未命中时先查 Redis 精确请求缓存，再进入 RAG。阈值默认 0.85，需用实际语料校准。详见 [使用、存储与失效规则](docs/faq-cache.md)。部署前执行数据库迁移到 `0013`。

## 可直接使用的知识库

基础业务目录已整理为人事与员工服务、财务与行政、IT 办公支持、账号与信息安全、产品使用指南、客户服务与工单、平台使用帮助，共 7 个库、129 份文档。前六类是合成业务资料，最后一类是当前平台操作说明。目录、源文件及整理边界见 [业务知识库说明](knowledge_library/README.md)。

## 原创示例库与召回测试

新增“青岚设备服务”示例库，8 份原创合成文档，26 道有答案题和 3 道无资料题。单库／统一检索均记录文档 Recall、逐字证据覆盖、跨文档题及失败案例，详见 [真实召回测试报告](evals/qinglan/report.md)。这是一套小样本开发测试，不是独立盲测。
