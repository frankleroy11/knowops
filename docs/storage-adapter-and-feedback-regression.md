# 存储适配器抽取 + 线上差评到离线回归的闭环

两件事一起做：把上传落盘逻辑从 HTTP 层抽到 `app/adapters/storage/`（消掉最后一个空壳目录），
以及把线上差评接进离线评测（候选集，人工复核后才并入冻结题集）。

## 1. 存储适配器（`app/adapters/storage/`）

| 文件 | 内容 |
|---|---|
| `local.py` | `LocalStorage`：`save()` 落盘 + SHA-256 指纹 + 限额校验；`path()`/`delete()`；`StoredFile`（文件名、存储名、哈希、大小） |
| `__init__.py` | 导出 `LocalStorage`、`StoredFile`、`ALLOWED_SUFFIXES` 与 `StorageError`/`UnsupportedFormat`/`FileTooLarge`/`EmptyFile` |
| `app/modules/knowledge/router.py` | 只保留薄包装 `store_upload()`：把存储错误映射为 415/413/422；`storage_backend()` 仍以模块级 `ROOT` 构造，便于测试替换 |
| `app/modules/ingestion/service.py` | 解析时通过 `LocalStorage(ROOT).path(...)` 取路径，不再手拼目录 |

设计要点：
- **存储层不依赖 FastAPI**：错误是 `StorageError` 子类，HTTP 状态码由路由决定；
- 落盘名仍是随机 UUID，客户端提供的路径会被剥掉（`../../etc/passwd.md` → `passwd.md`，有测试）；
- 任何失败（含超限、空文件）都会删除半成品文件——包括**超限时**，避免留下截断文件。

## 2. 上传文件的垃圾回收（`scripts/storage_gc.py`）

抽取过程中发现真实问题：`storage/` 里存在**未被任何版本引用的孤儿文件**。
排查时间戳确认是我此前几轮验收清理时"删了库里的行、没删盘上的文件"留下的（9 个）。

- 工具以 `document_versions.storage_path` 为唯一依据，列出孤儿文件；`--delete` 才真正删除；
- 忽略 `.gitkeep` 等点文件；输出计数便于核对；
- 已实际清理：引用 232 / 目录 233（含 `.gitkeep`）/ 孤儿 **0**。

> 顺带记录一条约束：`answer_feedback` 外键指向 `knowledge_bases`，所以删除知识库前必须先处理引用它的行。
> 未来做"删除知识库"功能时，需要按 `answer_feedback → kb_members → documents/versions/chunks → knowledge_bases`
> 的顺序清理（本次验收的清理脚本第一次就是踩了这个顺序问题）。

## 3. 线上差评 → 离线回归候选（`scripts/feedback_to_regression.py`）

**为什么**：离线评测只覆盖固定题集；差评是"这条回答有问题"的线上证据，应该能沉淀成回归题。

- `collect_candidates(rows)`：按问题文本归一化去重，保留最新一条差评，并带上
  `grounding_status`、`citation_count`、原因、所属知识库、出现次数与首/末次时间；
- `merge_candidates(existing, incoming)`：只刷新事实字段（次数、末次时间、拒绝状态、原因），
  **保留人工复核状态**（`review_status`/`reviewed_by` 等），因此可以反复运行而不丢结论；
- 输出是**新增文件**（默认 `evals/regressions/feedback_candidates.json`），
  并且**拒绝写入冻结题集**：`--out evals/questions.json` 或 `evals/holdout/**` 会直接报错退出；
- `--list` 查看现有候选与待复核数量。

这是"线上差评 → 人工复核 → 进入回归题集"这条链路的前半段；后半段（并入冻结题集）仍由人工完成，
本工具刻意不碰历史评测记录。

## 4. 验证

- `ruff check .` 通过；`pytest` **197 项通过**（新增 16 项：存储适配器 9、GC 3、回归候选 4）；
- **真实端到端验收 12/12 通过**（临时 8011 + 真实 MySQL + 真实 Celery worker + 真实 Milvus）：
  上传 `.md` → 存储名为 UUID + 后缀、文件确实落在 `storage/`、哈希为 64 位、worker 解析并 `indexed`；
  提交差评 → 脚本生成候选（保留 `model_refused` 与原因、状态 `pending`）→ `--list` 可用 →
  指向 `evals/questions.json` 与 `evals/holdout/questions.json` 均被拒绝写入；
- 验收数据已清理：用户 0、知识库 12、文档 232、切片 759、反馈 0、审计 0、Milvus 758 行、
  上传文件无孤儿、临时候选文件已删除。

## 5. 仍未做

- 正文/反馈数据删除时**自动**回收存储文件（目前靠 `storage_gc.py` 手动运行，可挂成定时任务）；
- 候选集并入冻结题集的人工流程尚未脚本化（有意保留人工判断）；
- 反馈保留策略与导出、差评样本自动重跑（用候选问题重新问答，判断是检索还是生成的问题）。
