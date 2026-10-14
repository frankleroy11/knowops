# P2：提交-审核-发布 + 审计日志 + 版本更新/下架同步

接续 [P0 认证授权](authorization-p0.md) 与 [P1 角色与成员管理](authorization-p1.md)。
本阶段的核心是**让“谁能改、改动何时生效”可追溯、可审核**，同时不破坏历史行为。

## 1. 交付内容

| 文件 | 作用 |
|---|---|
| `app/modules/audit/models.py`、`service.py`、`router.py` | 审计日志表、写入接口（自带提交）、`GET /admin/audit-logs`（仅管理员，可按 action/object_type 过滤） |
| `app/modules/knowledge/review.py` | 审核策略、发布、通过、驳回、下架、待审队列 |
| `app/modules/knowledge/router.py` | 上传按策略置状态；新版本上传、审核、下架接口；文档列表/详情返回 `review_status`/`is_current`/`retired_at`；知识库 `PATCH` 可开关审核 |
| `app/modules/retrieval/router.py`、`context.py` | 检索与邻接补全增加 `is_current` + `review_status=approved` 门控 |
| `app/modules/retrieval/service.py` | 索引改为**短事务**：先快照输入并置 `indexing`，再离线向量化，最后短事务写回结果 |
| `app/modules/ingestion/service.py`（未改） | 解析仍为单事务，但不再与长耗时索引互相阻塞 |
| `app/adapters/embeddings/local.py`、`app/core/config.py` | 新增 `EMBEDDING_OFFLINE`：权重已缓存且机器离线时，禁止联网 HEAD 检查 |
| `migrations/versions/0005_review_and_audit.py` | 新增 `audit_logs` 表与审核/发布/下架字段，并回填历史数据 |
| `frontend/src/App.vue`、`style.css` | 待审队列、上传新版本、下架、审核策略开关、审计日志面板 |
| `tests/test_review_audit.py`、`test_model_imports.py`、`test_embedding_offline.py` | 11 + 1 + 2 项测试 |

## 2. 关键语义

- **检索门控（唯一权威规则）**：一个版本可被检索，必须同时满足
  `status=parsed`、`VectorIndex.status=indexed`、`is_current=true`、`review_status=approved`。
- **审核按库可选**：`knowledge_bases.review_required` 默认 `false`，行为与历史一致（上传即生效）；
  开启后，非管理员的提交进入 `pending` 且 `is_current=false`，**通过审核才参与检索**。
- **管理员可直接发布**（不受待审限制）；**提交人不能审核自己的版本**（非管理员返回 409）。
- **版本更新**：新版本默认不替换旧版本；审核通过（或库未开启审核时上传即发布）才切换
  `is_current`，旧版本自动退出检索。旧切片与向量保留，便于追溯。
- **下架**：清空该文档的当前版本并记录 `retired_at`，不删除 MySQL 切片、不删除 Milvus 向量。
- **审计**：知识库创建/更新、上传、新版本、通过/驳回、下架、成员授予/移除、
  用户创建/改角色/启停、Token 签发/吊销全部落库；操作者身份以文本快照保存，用户改名删除后仍可追溯。
- 所有变更写入均沿用 P0/P1 的权限判定，未新增绕过路径。

## 3. 接口

| 接口 | 权限 | 说明 |
|---|---|---|
| `POST /documents/{id}/versions` | 库写权限 | 上传新版本（版本号自增） |
| `POST /documents/{id}/retire` | 库写权限 | 下架，退出检索 |
| `GET /knowledge-bases/{id}/reviews` | 库写权限 | 待审版本队列 |
| `POST /document-versions/{id}/review` | 库写权限 | `approve` / `reject`（带备注） |
| `PATCH /knowledge-bases/{id}` | 库写权限 | 开关 `review_required` |
| `GET /admin/audit-logs` | 管理员 | 最近审计记录，支持过滤 |

## 4. 验证

- `ruff check .` 通过；`pytest` **119 项通过**（P1 的 104 项 + 本阶段 15 项）；前端生产构建通过。
- 迁移 0005 已应用到真实 MySQL：232 条历史版本全部回填为 `approved` + `is_current=1`，
  12 个知识库 `review_required=0`，即**历史内容零行为变化**。
- **真实链路端到端验收 26/26 通过**（临时 8011 以 `AUTH_MODE=enforced` 运行，真实 MySQL、真实 Celery worker、
  真实 Milvus 与 BGE-M3）：建库 → editor 上传即刻可检索（首次索引含模型加载 10.6s）→ 开启审核 →
  非管理员上传进入 `pending` 且检索不到 → 队列可见 → 提交人自审 409 → 管理员通过后即可检索 →
  上传新版本时旧版本仍在线 → 通过后新版本生效、旧版本退出检索 → 下架后彻底检索不到 →
  审计覆盖 `kb.create/document.upload/document.version.upload/version.approve/document.retire/kb.update/kb.member.grant`。
- 验收结束后 MySQL 计数与 Milvus 行数均回到验收前（758 行），临时用户/Token/审计记录已删除。
- 界面：`/ui/` 提供的正是本次构建产物，且包含「待审版本 / 上传需审核 / 审计日志 / 上传新版本 / 已下架」等 P2 文案。
  Chrome headless 在本机沙箱下仍无法截图，**未做视觉验收**。

## 5. 验证中发现并修复的两个真实缺陷

1. **Celery worker 全部任务失败**（P0 引入，P2 验证时才暴露）
   - 现象：`NoReferencedTableError: Foreign key ... 'document_versions.reviewed_by' could not find table 'users'`。
   - 原因：worker 只导入 `app.modules.knowledge.models`，而该模块的外键指向 `users` 表；
     该表只在 API 进程里被导入，Celery 进程的 metadata 里不存在，于是**每次上传解析/索引都失败**。
   - 修复：在 `app/modules/knowledge/models.py` 内显式导入 `app.modules.auth.models` 完成表注册。
   - 守卫：`tests/test_model_imports.py` 在**子进程**中只导入 worker 会用到的模块并 `configure_mappers()`，
     避免被测试进程里已有的导入掩盖。
2. **索引持锁跨越向量化**（原有设计缺陷，被离线网络放大）
   - 现象：approve/retire 返回 500、清理 SQL 读超时；`innodb_trx` 显示一个事务持锁 400+ 秒，
     多个 `UPDATE document_versions` 处于 LOCK WAIT。
   - 原因：`index_version` 用 `SELECT ... FOR UPDATE` 包住整个流程，模型加载/向量化期间一直持有行锁。
     离线时模型加载要重试 5 次联网，锁被持有数分钟，阻塞同文档的审核/发布写入。
   - 修复：改为三段——短事务快照输入并把状态置为 `indexing`（对其他会话可见）→ 无事务向量化 → 短事务写回结果；
     重复投递可能重复向量化，但 upsert 按 chunk_id 幂等。
   - 守卫：`test_indexing_commits_progress_before_embedding` 断言 embedding 期间另一会话能看到 `indexing`。
     （注：最初写的“并发写成功”断言在 SQLite 上无法捕获旧行为，已实测并替换为可观测断言。）

## 6. 环境事件（已恢复，如实记录）

- `knowops-milvus-1` 于 2026-10-14 06:10 左右因子 etcd 会话中断退出（日志 `connection lost detected, shutting down`）。
  已用 `docker compose up -d milvus` 重启，**未删除任何数据卷**；集合
  `knowops_chunks_b5f83ff13a7f83fb` 与 758 行数据完好。
- `huggingface.co` 当前不可达（curl 10s 超时）。BGE-M3 权重在本机缓存完整（离线加载 10.4s，MPS，1024 维），
  卡住的原因是 sentence-transformers 每次加载都要做 HEAD 检查。已在 `.env` 增加 `EMBEDDING_OFFLINE=1`，
  并新增同名配置项；worker 与 API 已按此重启，索引恢复（首次约 10s，之后约 1–2s/文档）。
- 期间 MySQL 一度出现长事务持锁，已随 worker 重启与事务结束消失；当前无锁等待。

## 7. 未做（P3）

- SSO/OIDC、多租户、按部门继承授权。
- 用户名+密码登录、Token 过期与轮换、登录限流。
- 审核通知、审核 SLA、批量审核；前端仍未拆分单文件组件，未加前端自动化测试。
