# 项目完善：答案反馈闭环与包文档

两件事：补齐脚手架里**唯一没有实现的业务模块**（`feedback`），以及把 19 个空 `__init__.py`
改成自解释的包文档。

## 0. 先澄清一个误会

`__init__.py` 为空是 **Python 的正常写法**（包标记文件），不是"没写完"。
本项目 19 个空 `__init__.py` 中，只有两处目录是**真的只有骨架**：

- `app/modules/feedback/` —— 脚手架留的模块，此前从未实现（本次补齐）；
- `app/adapters/storage/` —— 空适配器；文件落盘逻辑目前内联在 `knowledge/router.py`（仍未迁移，见文末）。

## 1. 答案反馈闭环

### 为什么做
离线评测（`evals/`、`scripts/evaluate_*.py`）只能覆盖固定题集。真实用户对某条回答的评价，
连同它的 `grounding_status` 与引用数，是**线上那一半**的评测信号——生成质量回归不必等下一次跑脚本。

### 交付内容

| 文件 | 作用 |
|---|---|
| `app/modules/feedback/models.py` | `answer_feedback` 表：问题、答案、`grounding_status`、引用数、评分、原因、知识库与租户 |
| `app/modules/feedback/router.py` | `POST /feedback`（任意已认证用户）、`GET /admin/feedback`（含评分/知识库过滤）、`GET /admin/feedback/summary` |
| `migrations/versions/0010_answer_feedback.py` | 建表 + 4 个索引 |
| `frontend/src/App.vue` | 每条回答下 👍/👎，提交后显示"已记录反馈"；回答消息保留 `grounding_status` |
| `tests/test_feedback.py` | 9 项 |

### 关键语义
- **提交复用授权层**：带 `knowledge_base_id` 时走 `require_kb(..., "read")`——
  给一条自己读不到的回答打分会被拒（跨租户 404、同租户非成员 403）。
- **读取按租户收敛**：平台管理员看全部（可按 `rating`/`knowledge_base_id` 过滤），
  租户管理员只看本租户；非管理员 403。
- `summary` 给出总票数、有帮助比例与**按 `grounding_status` 的分布**——
  例如"拒答类回答的差评占比"一眼可见。
- **不重复写审计**：反馈行本身带 `tenant_id` 且可按租户读取，再写一条审计只增噪声；
  这是一个有意的取舍（与"每次状态变更都审计"的原则的差异已记录在此）。
- 本地免鉴权模式下 `user_id`/`tenant_id` 为 NULL（本地管理员无用户行），行为一致。

## 2. 包文档

19 个 `__init__.py` 各加一行用途说明，例如
`app.modules.feedback` → "答案反馈：把线上用户评价接入评测闭环"，
`app.modules.retrieval` → "语义检索、同文档邻接补全与向量索引"。
这样 `help(package)` 或看目录树就能明白职责，不再需要翻文件。

## 3. 验证

- `ruff check .` 通过；`pytest` **181 项通过**（新增 9 项反馈测试）；前端生产构建通过。
- 迁移 0010 已应用到真实 MySQL（`alembic current` = 0010）。
- **真实服务验收**（8010，off 模式即本地平台管理员）：
  提交 2 条反馈（一条带 `knowledge_base_id=10`、一条 `scope=all`）→ 列表按新旧返回 →
  `summary` 得到 `total=2, helpful=1, not_helpful=1, helpful_rate=0.5,
  by_grounding_status={quotes_validated:1, model_refused:1}` → 非法评分 422。
  其中被记下的 `model_refused` 恰好是之前诊断过的 NEW-09 拒答案例，
  说明这个闭环确实能收住线上质量问题。
- 验收数据已清理（`answer_feedback` 0 行，用户 0，知识库 12）。

## 4. 仍未做

- `app/adapters/storage/` 仍为空壳：上传的落盘/哈希/大小限制逻辑还在 `knowledge/router.py`，
  迁移到适配器是一次纯重构（行为不变、可被现有测试覆盖），留作后续。
- 反馈尚未接入评测脚本（例如把差评样本自动加进回归集）。
- 反馈的保留策略与导出。
