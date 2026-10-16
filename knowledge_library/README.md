# 业务知识库目录

`catalog.json` 将已有 `evals/corpus/` 的 126 份合成语料按业务主题重新分类，另加入 `platform/` 下 3 份当前平台帮助文档。语料仍为合成演示内容，不能作为真实企业的制度或服务承诺。

| 知识库 | 文档数量 |
| --- | ---: |
| 人事与员工服务 | 29 |
| 财务与行政 | 13 |
| IT 办公支持 | 25 |
| 账号与信息安全 | 17 |
| 产品使用指南 | 27 |
| 客户服务与工单 | 15 |
| 平台使用帮助 | 3 |

`faqs.json` 包含 3 条平台操作标准问答，证据来自平台帮助原文。

## 本机整理结果

新库全部重新上传、解析并索引，129 个文档版本均解析及索引成功，生成 466 个文本块和对应 Milvus 向量。全部采用 structure 字符切分策略快照。旧的 12 个入库验证、界面验收和重复评估库已按精确 ID 删除。原有 5 个演示账号保留，3 个普通用户均有新 7 个知识库的只读权限。

本轮移除的是在线知识库及对应索引／原始上传副本，没有删除 `evals/` 中的语料源文件、题集或历史评测结果。备份仅保存在本机忽略 Git 的 `.tmp/backups/kb-refresh-20261016/`，包含 MySQL、原文件及当时 758 条向量，带 SHA-256 校验与受限文件权限。备份含真实账号数据，不得提交或分享。

## 整理工具

```bash
PYTHONPATH=. python scripts/refresh_business_library.py
# 确认本地备份已完成且校验正确，使用专用 API；该操作会删除匹配快照的旧测试库。
CHUNK_STRATEGY=structure python -m uvicorn app.main:app --host 127.0.0.1 --port 8011
PYTHONPATH=. python scripts/refresh_business_library.py --apply --backup .tmp/backups/kb-refresh-20261016
```

工具只处理本演示环境 tenant_id=1，默认预览。应用模式先创建新库、上传并检查所有版本，做逐库真实检索，保留普通用户授权并建立平台 FAQ，最后删除快照中以“入库验证-”“界面验收-”“页面操作验收”“评估-”命名的旧库。旧库名称变更时停止，不扩展删除范围。运行状态和源文件摘要保存于 `.tmp/business-library-refresh.json`，已有完成状态时不会再次修改数据库。

备份前必须先停止本项目 API 与 Worker；SQL 和原文件备份可用 `scripts/backup_local.py`，该工具本身不备份 Milvus。本次另外导出了当前集合向量，所以本整理工具要求备份清单中也存在 `milvus-vectors.json`。备份不是已经验证过的自动恢复流程；需要恢复时应先隔离环境核验快照，再处理 SQL、文件与向量，不能把备份 JSON 当成可直接覆盖运行库的指令。

## 验证与限制

7 个库均通过真实 BGE-M3 / Milvus 检索；5 个账号均能看到新目录，3 条 FAQ 在统一问答中命中。另测两道 RAG 题：一线城市交通费回答成功；“解析完成是否意味着文档已经可以检索？”出现一次模型拒答，失败原始结果保留于 [验收记录](../evals/library_refresh/acceptance-20261016.json)。因此不宣称所有问题都能回答或质量评测全通过。
