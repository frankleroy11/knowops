# KnowOps 评估数据集：星桥科技（虚构）

本目录是项目的**固定评估集**，用于回答一个具体问题：这套 RAG 链路在什么情况下会失败，以及优化后有没有变好。

> **声明**：全部语料为合成内容，虚构企业「星桥科技」，不对应任何真实企业制度、产品或人员。
> 指标只代表在该合成语料上的表现，**不能**作为真实企业准确率、生产性能或上线经历的依据。

## 一、目录结构

```text
evals/
  corpus/
    it/         IT 支持知识库（40 份 .md + 2 份 .pdf 附录）
    hr/         人事制度知识库（40 份 .md + 2 份 .pdf 附录）
    product/    产品与客服知识库（40 份 .md + 2 份 .pdf 附录）
  facts/        事实标注源（每行一条 JSON），题集由它装配而来
    it.jsonl / hr.jsonl / product.jsonl
    check_it.py / check_hr.py / check_product.py   写手自检脚本
  tools/
    build_questions.py   校验标注并装配 questions.json + manifest.json
    build_pdfs.py        生成 PDF 附录（纯标准库，ASCII 正文）
  questions.json         评估题集（由 facts 装配，勿手改）
  manifest.json          语料哈希、题集哈希、题量与难度分布
  pdf_appendix.json      PDF 附录清单与页码信息
  runs/<时间戳>/          每次评估的 metadata.json / results.json / report.md
  legacy/                上一版 30 题小数据集与它的一次基线 run，保留用于对照
```

## 二、这个数据集为什么不是"越多越好"

上一版数据集只有 6 份文档、2.2 KB 文字，指标全是满分（Recall@3 = 1.0）。那不是系统强，而是**题目太容易**：
语料只有一段，提问用词和原文几乎一致，检索没有失败空间。这种数据写进简历经不起追问。

本版数据集的目的是**制造真实失败**，因此刻意埋入：

| 难点 | 埋法 | 检验什么 |
|---|---|---|
| 术语变体 | 文档写"动态验证码"，提问说"手机令牌" | 语义检索是否真的理解近义表达 |
| 数字密集 | 同一主题多份文档数字不同（8 小时 / 30 分钟 / 5 次） | 是否只靠词面相似就命中 |
| 标题极像 | 《VPN 使用指南（北京）》《（上海）》结论不同 | 是否被标题相似度误导 |
| 已废止旧制度 | 旧文档写明"自 X 年 X 月废止，以《Y》为准" | 是否命中失效信息并错误引用 |
| 同词不同意 | "账号锁定"在 VPN/邮箱/AD 三处阈值不同 | 多文档歧义下的排序能力 |
| 跨文档答案 | 答案分列两份文档，expected_sources 有两个 | 是否只召回一份就当作完整 |
| 表格数值 | 审批分档、配额表、错误码表 | 结构化数值是否被正确检索 |
| 跨库隔离 | 问题答案只存在于另一个知识库 | 知识库过滤是否真的生效 |

## 三、题集构成

每题库 40 篇文档 + 56 条标注，共 3 库 **168 条标注**，装配后为 150 题：

| 类型 | 数量 | 说明 |
|---|---|---|
| answerable | 每库 34（共 102） | 有明确答案，按难度分 easy / paraphrase / numeric / multi_source |
| refusal | 每库 16（共 48） | 期望拒答：10 条真缺失 + 6 条"看似有答案但语料无此细节" |
| cross_kb | 每库 6（共 18） | 问题可被源库回答，但提问指向别的库，期望拒答 |

`split` 字段把题目分成 `dev` / `test`：调参看 dev，汇报看 test。拒答题全部进 test，
避免被 dev 调参"优化掉"。

## 四、标注可信性如何保证

题集不是手写的 `questions.json`，而是从 `facts/*.jsonl` 装配出来的，且每条标注都要通过机械校验
（`python evals/tools/build_questions.py`）：

1. `expected_sources` 里的文件名必须真实存在于对应语料目录；
2. `terms` 里的每个片段必须**逐字**出现在源文件正文中——这是"答案确实出自该文档"的证据；
3. answerable 的 `reference_answer` 非空；refusal 的 `expected_sources` 与 `reference_answer` 必须为空；
4. 题量与难度分布必须匹配约定，任何不符都会让脚本非零退出。

因此"标注与语料不一致"这类问题在评估前就会被挡住，而不是等指标异常才发现。

## 五、如何运行

```bash
conda activate knowops

# 1) 校验标注并重新装配题集（改了 facts 才需要）
python evals/tools/build_questions.py

# 2) 生成 PDF 附录（可选，需要基准 Markdown 已存在）
python evals/tools/build_pdfs.py

# 3) 真实评估：入库 3 个知识库 → 等索引 → 逐题检索与问答
python scripts/evaluate_v2.py                # 全量
python scripts/evaluate_v2.py --split test   # 只看 test
python scripts/evaluate_v2.py --skip-chat    # 只评检索，不调用大模型（省钱、快）
python scripts/evaluate_v2.py --reuse        # 复用已入库的知识库，跳过上传
```

评估脚本会创建名为 `评估-<run-label>-<库名>` 的知识库并**保留数据**（与旧版一致），
知识库按稳定名称复用，重复运行不会不断堆积新库。输出写入 `evals/runs/<北京时间>/`。

## 六、指标口径与已知局限

| 指标 | 口径 | 局限 |
|---|---|---|
| source_recall_at_k | 前 k 个结果的**文档**是否覆盖全部标注来源 | 文档级偏松：命中文档不等于命中答案所在段落 |
| chunk_recall_at_1 / at_k | 前 k 个结果中是否存在**同时**命中标注来源文件与标注 terms 的切片 | 依赖 terms 标注质量；同义改写可能让"正确切片"判定偏严 |
| mrr_at_k | 第一个相关切片排名的倒数均值 | 未区分"部分正确" |
| ndcg_at_k | 二值相关性的 nDCG@k | 相关性只有 0/1，信息量弱于多级标注，**不衡量答案正确性** |
| refusal_accuracy | 期望拒答题是否返回 answerable=false 且无引用 | 不等于抗提示注入能力 |
| citation_source_match_rate | 引用文件集合是否与标注来源一致 | 只查文档级出处，不验证逐句事实 |
| keyword_pass_rate_heuristic_only | 预设关键词是否出现 | **不是正确率**，只作为人工复核线索 |

另外必须说明：

- 语料为合成数据，规模（约 126 份文档）远小于真实企业知识库，**不能**外推到大库上的表现；
- 大模型回答质量仍以 `report.md` 的人工复核列为准，未引入自动裁判；
- PDF 附录正文为 ASCII（内置标准字体不含 CJK 字形），仅用于验证解析与页码溯源，
  不代表中文 PDF 的版式解析能力；
- 检索指标只反映「BGE-M3 + Milvus 向量检索」这一条链路，重排序与混合检索属于后续阶段。

## 七、与旧数据集的关系

旧数据集（6 份文档、30 题、一次基线 run）已完整归档到 `evals/legacy/`，包括它当时的
`corpus/`、`questions.json` 与 `runs/`。归档而不是删除的原因：那次 run 是"链路已跑通"的历史证据，
删除后无法复现。旧流程脚本 `scripts/evaluate.py` 保持原样，便于对照两版数据集的难度差异。

## 修正后的检索评估口径（evidence-v3）

`scripts/evaluate_v2.py --run-label synthetic-v1 --reuse --skip-chat --top-k 3`
复用既有入库数据；可将 top-k 改为 5 或 10。运行结果新增 metric_version，旧版运行记录保持原样。

- 根据 isolation 字段识别 18 道跨库题，不依赖旧的 kind=answerable 标签。
  当前实际有答案题 102 道，期望拒答题 66（含 18 道隔离题）。
- chunk_recall_at_1：只有第一条切片是否覆盖全部标注证据。
- evidence_complete_at_k（chunk_recall_at_k 为兼容别名）：各来源所需证据能否被前 k 条切片联合覆盖。
  它是逐题完整覆盖率，不是“相关切片数量 / 全部相关切片”的传统 Recall。
- 对每个来源按其原文归属分配 terms，允许不同切片共同支持多文档答案。
- MRR：第一个包含标注证据的切片排名倒数；不代表完整答案已召回。
- nDCG：重复来源只记第一次支持证据，理想值使用全部标注来源数，缺失来源会被惩罚。
- HTTP 错误保留在对应题型分母中。
- cross_kb_leakage 对照 MySQL 中文档所属知识库；知识库没有泄漏不代表必须拒答，
  因为其他库可能有重叠制度。跨库正确拒答需结合标注与原文复核。
- skip-chat 不输出生成/拒答表现，不能将未调用生成的题目当作正确拒答。

HR-32 有一个标注来源没有对应 terms，单独记录 evidence_label_error。文档级统计仍包含它，
证据覆盖/MRR/nDCG 暂排除该题并报告 evidence_evaluable_questions；其他 HTTP 失败仍计入分母。
三组修正基线与失败示例见 docs/retrieval-baseline-corrected.md。

## 等价证据补充（reviewed-alternatives-v1）

`evidence_annotations.json` 保存独立的逐题补充，不改写原 questions.json、facts 或 manifest。
当前包含六道已诊断 dev 题的等价证据组，以及 HR-32 的客观证据遗漏补充。
每个必需事实都要匹配一个允许来源中的完整片段，多个事实可以分别由不同切片支持。
标注由助手对照原文复核，仍待独立人工确认；不是模型自动生成金标准。

评估同时返回原始 `evidence_complete_at_k` 和补充口径 `accepted_evidence_complete_at_k`，
HR-32 原始标注缺口仍保留于旧指标，新指标使用补充后的证据判定。
新增口径不自动将任意相似文件视为正确来源；它只接受逐条列出的来源/片段。
未来修改问题或来源时，必须重新核验补充标注。运行时校验 question/domain 一致及 quote 存在。

`python scripts/rescore_evidence.py` 仅对存档 dev 候选和分数重算指标，不发起检索或大模型调用。
结果位于 annotation_runs/，解释与修改依据见 docs/evidence-annotation-review.md。
本次已诊断过的六题不是独立盲测集，不能将修正后的增益解释为泛化能力提升。
