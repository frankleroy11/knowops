# KnowOps 星桥科技合成数据集评估

**重要声明**：本数据集全部为合成内容（虚构企业「星桥科技」），不对应任何真实企业制度、产品或人员。指标只代表在该合成语料上的表现，**不能**作为真实企业准确率或生产性能依据。

- 运行标识：synthetic-v1
- 题数：168（102 有答案 / 66 期望拒答）
- 知识库：it=评估-synthetic-v1-IT 支持, hr=评估-synthetic-v1-人事制度, product=评估-synthetic-v1-产品与客服
- 证据覆盖：分别在各标注来源的切片中匹配该来源的 terms；允许跨切片联合覆盖。
- Recall@1 仅检查第一条；MRR 检查首个支持证据；nDCG 按不同来源去重，理想值包含未召回来源。
- 隔离题单列，计入期望拒答题；无泄漏与正确拒答是两个不同指标。

## 自动指标

```json
{
  "questions": 168,
  "successful_requests": 168,
  "answerable_questions": 102,
  "refusal_questions": 66,
  "isolation_questions": 18,
  "isolation_checked_requests": 18,
  "evidence_evaluable_questions": 101,
  "evidence_label_errors": 1,
  "isolation_leakage_rate": 0.0,
  "evidence_complete_at_k": 0.6832,
  "source_recall_at_k": 0.8627,
  "chunk_recall_at_1": 0.297,
  "chunk_recall_at_k": 0.6832,
  "mrr_at_k": 0.5939,
  "ndcg_at_k": 0.6169,
  "timings_ms": {
    "retrieval": {
      "p50": 390.66,
      "p95": 401.53
    },
    "chat": {
      "p50": null,
      "p95": null
    }
  }
}
```

## 按难度分组（有答案题）

```json
{
  "cross_kb": {
    "questions": 18,
    "successful_requests": 18,
    "answerable_questions": 0,
    "refusal_questions": 18,
    "isolation_questions": 18,
    "isolation_checked_requests": 18,
    "evidence_evaluable_questions": 0,
    "evidence_label_errors": 0,
    "isolation_leakage_rate": 0.0,
    "evidence_complete_at_k": null,
    "source_recall_at_k": null,
    "chunk_recall_at_1": null,
    "chunk_recall_at_k": null,
    "mrr_at_k": null,
    "ndcg_at_k": null,
    "timings_ms": {
      "retrieval": {
        "p50": 385.43,
        "p95": 401.44
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "easy": {
    "questions": 24,
    "successful_requests": 24,
    "answerable_questions": 24,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_checked_requests": 0,
    "evidence_evaluable_questions": 24,
    "evidence_label_errors": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.75,
    "source_recall_at_k": 0.9583,
    "chunk_recall_at_1": 0.375,
    "chunk_recall_at_k": 0.75,
    "mrr_at_k": 0.5555,
    "ndcg_at_k": 0.6051,
    "timings_ms": {
      "retrieval": {
        "p50": 390.76,
        "p95": 400.07
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "multi_source": {
    "questions": 18,
    "successful_requests": 18,
    "answerable_questions": 18,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_checked_requests": 0,
    "evidence_evaluable_questions": 17,
    "evidence_label_errors": 1,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.2353,
    "source_recall_at_k": 0.6111,
    "chunk_recall_at_1": 0.0,
    "chunk_recall_at_k": 0.2353,
    "mrr_at_k": 0.7392,
    "ndcg_at_k": 0.5992,
    "timings_ms": {
      "retrieval": {
        "p50": 388.79,
        "p95": 398.95
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "numeric": {
    "questions": 30,
    "successful_requests": 30,
    "answerable_questions": 30,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_checked_requests": 0,
    "evidence_evaluable_questions": 30,
    "evidence_label_errors": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.7333,
    "source_recall_at_k": 0.9,
    "chunk_recall_at_1": 0.3333,
    "chunk_recall_at_k": 0.7333,
    "mrr_at_k": 0.5055,
    "ndcg_at_k": 0.5639,
    "timings_ms": {
      "retrieval": {
        "p50": 390.79,
        "p95": 398.46
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "paraphrase": {
    "questions": 30,
    "successful_requests": 30,
    "answerable_questions": 30,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_checked_requests": 0,
    "evidence_evaluable_questions": 30,
    "evidence_label_errors": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.8333,
    "source_recall_at_k": 0.9,
    "chunk_recall_at_1": 0.3667,
    "chunk_recall_at_k": 0.8333,
    "mrr_at_k": 0.6305,
    "ndcg_at_k": 0.6895,
    "timings_ms": {
      "retrieval": {
        "p50": 391.24,
        "p95": 409.5
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "refusal": {
    "questions": 48,
    "successful_requests": 48,
    "answerable_questions": 0,
    "refusal_questions": 48,
    "isolation_questions": 0,
    "isolation_checked_requests": 0,
    "evidence_evaluable_questions": 0,
    "evidence_label_errors": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": null,
    "source_recall_at_k": null,
    "chunk_recall_at_1": null,
    "chunk_recall_at_k": null,
    "mrr_at_k": null,
    "ndcg_at_k": null,
    "timings_ms": {
      "retrieval": {
        "p50": 390.56,
        "p95": 405.46
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  }
}
```

## 按 dev / test 分组

```json
{
  "dev": {
    "questions": 73,
    "successful_requests": 73,
    "answerable_questions": 62,
    "refusal_questions": 11,
    "isolation_questions": 11,
    "isolation_checked_requests": 11,
    "evidence_evaluable_questions": 62,
    "evidence_label_errors": 0,
    "isolation_leakage_rate": 0.0,
    "evidence_complete_at_k": 0.6935,
    "source_recall_at_k": 0.871,
    "chunk_recall_at_1": 0.3226,
    "chunk_recall_at_k": 0.6935,
    "mrr_at_k": 0.6425,
    "ndcg_at_k": 0.6577,
    "timings_ms": {
      "retrieval": {
        "p50": 391.17,
        "p95": 400.23
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "test": {
    "questions": 95,
    "successful_requests": 95,
    "answerable_questions": 40,
    "refusal_questions": 55,
    "isolation_questions": 7,
    "isolation_checked_requests": 7,
    "evidence_evaluable_questions": 39,
    "evidence_label_errors": 1,
    "isolation_leakage_rate": 0.0,
    "evidence_complete_at_k": 0.6667,
    "source_recall_at_k": 0.85,
    "chunk_recall_at_1": 0.2564,
    "chunk_recall_at_k": 0.6667,
    "mrr_at_k": 0.5167,
    "ndcg_at_k": 0.5522,
    "timings_ms": {
      "retrieval": {
        "p50": 390.56,
        "p95": 403.49
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  }
}
```

## 按知识库分组

```json
{
  "hr": {
    "questions": 56,
    "successful_requests": 56,
    "answerable_questions": 34,
    "refusal_questions": 22,
    "isolation_questions": 6,
    "isolation_checked_requests": 6,
    "evidence_evaluable_questions": 33,
    "evidence_label_errors": 1,
    "isolation_leakage_rate": 0.0,
    "evidence_complete_at_k": 0.697,
    "source_recall_at_k": 0.9412,
    "chunk_recall_at_1": 0.1818,
    "chunk_recall_at_k": 0.697,
    "mrr_at_k": 0.5136,
    "ndcg_at_k": 0.5583,
    "timings_ms": {
      "retrieval": {
        "p50": 391.36,
        "p95": 405.46
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "it": {
    "questions": 56,
    "successful_requests": 56,
    "answerable_questions": 34,
    "refusal_questions": 22,
    "isolation_questions": 6,
    "isolation_checked_requests": 6,
    "evidence_evaluable_questions": 34,
    "evidence_label_errors": 0,
    "isolation_leakage_rate": 0.0,
    "evidence_complete_at_k": 0.7353,
    "source_recall_at_k": 0.8235,
    "chunk_recall_at_1": 0.4706,
    "chunk_recall_at_k": 0.7353,
    "mrr_at_k": 0.7255,
    "ndcg_at_k": 0.7218,
    "timings_ms": {
      "retrieval": {
        "p50": 391.97,
        "p95": 400.23
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "product": {
    "questions": 56,
    "successful_requests": 56,
    "answerable_questions": 34,
    "refusal_questions": 22,
    "isolation_questions": 6,
    "isolation_checked_requests": 6,
    "evidence_evaluable_questions": 34,
    "evidence_label_errors": 0,
    "isolation_leakage_rate": 0.0,
    "evidence_complete_at_k": 0.6176,
    "source_recall_at_k": 0.8235,
    "chunk_recall_at_1": 0.2353,
    "chunk_recall_at_k": 0.6176,
    "mrr_at_k": 0.5402,
    "ndcg_at_k": 0.5691,
    "timings_ms": {
      "retrieval": {
        "p50": 388.81,
        "p95": 401.57
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  }
}
```

## 逐题结果

|题号|库|难度|类型|文档命中|切片命中|MRR|引用匹配|正确拒答|
|---|---|---|---|---|---|---|---|---|
|HR-01|hr|easy|answerable|True|True|0.3333|-|-|
|HR-02|hr|easy|answerable|True|True|0.5|-|-|
|HR-03|hr|easy|answerable|True|True|1.0|-|-|
|HR-04|hr|easy|answerable|True|True|0.3333|-|-|
|HR-05|hr|easy|answerable|True|True|0.5|-|-|
|HR-06|hr|easy|answerable|True|True|1.0|-|-|
|HR-07|hr|easy|answerable|True|False|0.0|-|-|
|HR-08|hr|easy|answerable|True|True|0.5|-|-|
|HR-09|hr|paraphrase|answerable|True|False|0.0|-|-|
|HR-10|hr|paraphrase|answerable|True|True|0.25|-|-|
|HR-11|hr|paraphrase|answerable|True|True|1.0|-|-|
|HR-12|hr|paraphrase|answerable|True|True|0.5|-|-|
|HR-13|hr|paraphrase|answerable|True|True|0.5|-|-|
|HR-14|hr|paraphrase|answerable|True|True|1.0|-|-|
|HR-15|hr|paraphrase|answerable|True|True|0.5|-|-|
|HR-16|hr|paraphrase|answerable|True|True|1.0|-|-|
|HR-17|hr|paraphrase|answerable|True|True|0.3333|-|-|
|HR-18|hr|paraphrase|answerable|True|True|1.0|-|-|
|HR-19|hr|numeric|answerable|True|False|0.0|-|-|
|HR-20|hr|numeric|answerable|True|False|0.0|-|-|
|HR-21|hr|numeric|answerable|True|False|0.0|-|-|
|HR-22|hr|numeric|answerable|True|False|0.0|-|-|
|HR-23|hr|numeric|answerable|True|True|1.0|-|-|
|HR-24|hr|numeric|answerable|True|True|1.0|-|-|
|HR-25|hr|numeric|answerable|True|True|1.0|-|-|
|HR-26|hr|numeric|answerable|True|True|0.5|-|-|
|HR-27|hr|numeric|answerable|True|True|0.3333|-|-|
|HR-28|hr|numeric|answerable|True|True|0.3333|-|-|
|HR-29|hr|multi_source|answerable|True|False|0.3333|-|-|
|HR-30|hr|multi_source|answerable|True|False|0.2|-|-|
|HR-31|hr|multi_source|answerable|False|False|0.0|-|-|
|HR-32|hr|multi_source|answerable|True|-|-|-|-|
|HR-33|hr|multi_source|answerable|True|True|1.0|-|-|
|HR-34|hr|multi_source|answerable|False|False|1.0|-|-|
|HR-35|hr|refusal|refusal|-|-|-|-|-|
|HR-36|hr|refusal|refusal|-|-|-|-|-|
|HR-37|hr|refusal|refusal|-|-|-|-|-|
|HR-38|hr|refusal|refusal|-|-|-|-|-|
|HR-39|hr|refusal|refusal|-|-|-|-|-|
|HR-40|hr|refusal|refusal|-|-|-|-|-|
|HR-41|hr|refusal|refusal|-|-|-|-|-|
|HR-42|hr|refusal|refusal|-|-|-|-|-|
|HR-43|hr|refusal|refusal|-|-|-|-|-|
|HR-44|hr|refusal|refusal|-|-|-|-|-|
|HR-45|hr|refusal|refusal|-|-|-|-|-|
|HR-46|hr|refusal|refusal|-|-|-|-|-|
|HR-47|hr|refusal|refusal|-|-|-|-|-|
|HR-48|hr|refusal|refusal|-|-|-|-|-|
|HR-49|hr|refusal|refusal|-|-|-|-|-|
|HR-50|hr|refusal|refusal|-|-|-|-|-|
|HR-51|hr|cross_kb|answerable|-|-|-|-|-|
|HR-52|hr|cross_kb|answerable|-|-|-|-|-|
|HR-53|hr|cross_kb|answerable|-|-|-|-|-|
|HR-54|hr|cross_kb|answerable|-|-|-|-|-|
|HR-55|hr|cross_kb|answerable|-|-|-|-|-|
|HR-56|hr|cross_kb|answerable|-|-|-|-|-|
|IT-01|it|easy|answerable|False|False|0.0|-|-|
|IT-02|it|easy|answerable|True|False|0.0|-|-|
|IT-03|it|easy|answerable|True|True|1.0|-|-|
|IT-04|it|easy|answerable|True|True|1.0|-|-|
|IT-05|it|easy|answerable|True|True|1.0|-|-|
|IT-06|it|easy|answerable|True|True|1.0|-|-|
|IT-07|it|easy|answerable|True|True|1.0|-|-|
|IT-08|it|easy|answerable|True|True|0.3333|-|-|
|IT-09|it|paraphrase|answerable|True|False|1.0|-|-|
|IT-10|it|paraphrase|answerable|True|True|1.0|-|-|
|IT-11|it|paraphrase|answerable|True|True|1.0|-|-|
|IT-12|it|paraphrase|answerable|True|True|0.3333|-|-|
|IT-13|it|paraphrase|answerable|True|True|1.0|-|-|
|IT-14|it|paraphrase|answerable|True|True|1.0|-|-|
|IT-15|it|paraphrase|answerable|True|True|1.0|-|-|
|IT-16|it|paraphrase|answerable|True|True|1.0|-|-|
|IT-17|it|paraphrase|answerable|True|True|1.0|-|-|
|IT-18|it|paraphrase|answerable|True|True|0.3333|-|-|
|IT-19|it|numeric|answerable|True|True|1.0|-|-|
|IT-20|it|numeric|answerable|False|False|0.0|-|-|
|IT-21|it|numeric|answerable|False|False|0.0|-|-|
|IT-22|it|numeric|answerable|True|True|1.0|-|-|
|IT-23|it|numeric|answerable|True|True|1.0|-|-|
|IT-24|it|numeric|answerable|True|True|0.5|-|-|
|IT-25|it|numeric|answerable|True|True|1.0|-|-|
|IT-26|it|numeric|answerable|True|True|0.5|-|-|
|IT-27|it|numeric|answerable|True|True|0.3333|-|-|
|IT-28|it|numeric|answerable|True|True|0.5|-|-|
|IT-29|it|multi_source|answerable|False|False|1.0|-|-|
|IT-30|it|multi_source|answerable|True|False|1.0|-|-|
|IT-31|it|multi_source|answerable|False|False|0.5|-|-|
|IT-32|it|multi_source|answerable|True|True|1.0|-|-|
|IT-33|it|multi_source|answerable|True|True|0.3333|-|-|
|IT-34|it|multi_source|answerable|False|False|1.0|-|-|
|IT-35|it|refusal|refusal|-|-|-|-|-|
|IT-36|it|refusal|refusal|-|-|-|-|-|
|IT-37|it|refusal|refusal|-|-|-|-|-|
|IT-38|it|refusal|refusal|-|-|-|-|-|
|IT-39|it|refusal|refusal|-|-|-|-|-|
|IT-40|it|refusal|refusal|-|-|-|-|-|
|IT-41|it|refusal|refusal|-|-|-|-|-|
|IT-42|it|refusal|refusal|-|-|-|-|-|
|IT-43|it|refusal|refusal|-|-|-|-|-|
|IT-44|it|refusal|refusal|-|-|-|-|-|
|IT-45|it|refusal|refusal|-|-|-|-|-|
|IT-46|it|refusal|refusal|-|-|-|-|-|
|IT-47|it|refusal|refusal|-|-|-|-|-|
|IT-48|it|refusal|refusal|-|-|-|-|-|
|IT-49|it|refusal|refusal|-|-|-|-|-|
|IT-50|it|refusal|refusal|-|-|-|-|-|
|IT-51|it|cross_kb|answerable|-|-|-|-|-|
|IT-52|it|cross_kb|answerable|-|-|-|-|-|
|IT-53|it|cross_kb|answerable|-|-|-|-|-|
|IT-54|it|cross_kb|answerable|-|-|-|-|-|
|IT-55|it|cross_kb|answerable|-|-|-|-|-|
|IT-56|it|cross_kb|answerable|-|-|-|-|-|
|PD-01|product|easy|answerable|True|False|0.0|-|-|
|PD-02|product|easy|answerable|True|False|0.0|-|-|
|PD-03|product|easy|answerable|True|True|1.0|-|-|
|PD-04|product|easy|answerable|True|False|0.0|-|-|
|PD-05|product|easy|answerable|True|True|0.5|-|-|
|PD-06|product|easy|answerable|True|True|1.0|-|-|
|PD-07|product|easy|answerable|True|True|0.3333|-|-|
|PD-08|product|easy|answerable|True|True|1.0|-|-|
|PD-09|product|paraphrase|answerable|True|True|0.3333|-|-|
|PD-10|product|paraphrase|answerable|True|True|0.25|-|-|
|PD-11|product|paraphrase|answerable|False|False|0.0|-|-|
|PD-12|product|paraphrase|answerable|False|False|0.0|-|-|
|PD-13|product|paraphrase|answerable|True|True|0.3333|-|-|
|PD-14|product|paraphrase|answerable|False|False|0.0|-|-|
|PD-15|product|paraphrase|answerable|True|True|1.0|-|-|
|PD-16|product|paraphrase|answerable|True|True|1.0|-|-|
|PD-17|product|paraphrase|answerable|True|True|1.0|-|-|
|PD-18|product|paraphrase|answerable|True|True|0.25|-|-|
|PD-19|product|numeric|answerable|True|True|1.0|-|-|
|PD-20|product|numeric|answerable|True|True|0.3333|-|-|
|PD-21|product|numeric|answerable|True|True|0.3333|-|-|
|PD-22|product|numeric|answerable|True|True|1.0|-|-|
|PD-23|product|numeric|answerable|True|True|1.0|-|-|
|PD-24|product|numeric|answerable|True|True|0.5|-|-|
|PD-25|product|numeric|answerable|True|True|0.5|-|-|
|PD-26|product|numeric|answerable|True|True|0.5|-|-|
|PD-27|product|numeric|answerable|False|False|0.0|-|-|
|PD-28|product|numeric|answerable|True|False|0.0|-|-|
|PD-29|product|multi_source|answerable|True|False|1.0|-|-|
|PD-30|product|multi_source|answerable|False|False|1.0|-|-|
|PD-31|product|multi_source|answerable|False|False|0.2|-|-|
|PD-32|product|multi_source|answerable|True|False|1.0|-|-|
|PD-33|product|multi_source|answerable|True|True|1.0|-|-|
|PD-34|product|multi_source|answerable|True|False|1.0|-|-|
|PD-35|product|refusal|refusal|-|-|-|-|-|
|PD-36|product|refusal|refusal|-|-|-|-|-|
|PD-37|product|refusal|refusal|-|-|-|-|-|
|PD-38|product|refusal|refusal|-|-|-|-|-|
|PD-39|product|refusal|refusal|-|-|-|-|-|
|PD-40|product|refusal|refusal|-|-|-|-|-|
|PD-41|product|refusal|refusal|-|-|-|-|-|
|PD-42|product|refusal|refusal|-|-|-|-|-|
|PD-43|product|refusal|refusal|-|-|-|-|-|
|PD-44|product|refusal|refusal|-|-|-|-|-|
|PD-45|product|refusal|refusal|-|-|-|-|-|
|PD-46|product|refusal|refusal|-|-|-|-|-|
|PD-47|product|refusal|refusal|-|-|-|-|-|
|PD-48|product|refusal|refusal|-|-|-|-|-|
|PD-49|product|refusal|refusal|-|-|-|-|-|
|PD-50|product|refusal|refusal|-|-|-|-|-|
|PD-51|product|cross_kb|answerable|-|-|-|-|-|
|PD-52|product|cross_kb|answerable|-|-|-|-|-|
|PD-53|product|cross_kb|answerable|-|-|-|-|-|
|PD-54|product|cross_kb|answerable|-|-|-|-|-|
|PD-55|product|cross_kb|answerable|-|-|-|-|-|
|PD-56|product|cross_kb|answerable|-|-|-|-|-|

## 人工复核

逐题核对答案正确性与原文支持程度；未复核题目的人工分数留空。

### HR-01 每个月几号发工资？遇到周末会提前吗？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：薪酬结构与发薪日历说明.md

检索来源：薪酬结构与发薪日历说明.md, 薪酬结构与发薪日历说明.md, 薪酬结构与发薪日历说明.md, 值班与加班补贴说明.md, 员工关系与假期常见问题 FAQ.md

参考：每月 15 日发放上一个自然月的工资；遇法定节假日或双休日提前至最近一个工作日。

实际：未调用生成

引用：无

人工结论：待复核

### HR-02 公积金公司和个人各交多少？

难度：easy ｜ 库：hr ｜ split：test

标注来源：社会保险与住房公积金管理办法.md

检索来源：社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 报销与出差常见问题 FAQ.md, 补充医疗保险与年度体检福利说明.md

参考：公司与个人缴存比例均为 12%，缴存基数与社保基数一致。

实际：未调用生成

引用：无

人工结论：待复核

### HR-03 婚假有几天？什么时候必须休完？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：请假与休假管理制度.md

检索来源：请假与休假管理制度.md, 员工关系与假期常见问题 FAQ.md, 请假与休假管理制度.md, 请假类型与假期额度对照表.md, 请假类型与假期额度对照表.md

参考：婚假 10 个自然日，须在领取结婚证之日起 12 个月内休完。

实际：未调用生成

引用：无

人工结论：待复核

### HR-04 公司年度体检的标准是多少钱？

难度：easy ｜ 库：hr ｜ split：test

标注来源：补充医疗保险与年度体检福利说明.md

检索来源：补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md, 报销与出差常见问题 FAQ.md

参考：1200 元/人；40 周岁及以上员工为 2000 元/人。

实际：未调用生成

引用：无

人工结论：待复核

### HR-05 春节公司发什么福利？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：节日福利与团建经费管理办法.md

检索来源：节日福利与团建经费管理办法.md, 节日福利与团建经费管理办法.md, 节日福利与团建经费管理办法.md, 报销与出差常见问题 FAQ.md, 年终奖与绩效奖金发放办法.md

参考：800 元/人的实物礼包加平台积分。

实际：未调用生成

引用：无

人工结论：待复核

### HR-06 辞职要提前多久通知公司？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：离职管理与工作交接流程.md

检索来源：离职管理与工作交接流程.md, 员工关系与假期常见问题 FAQ.md, 离职管理与工作交接流程.md, 离职证明与竞业限制说明.md, 离职管理与工作交接流程.md

参考：正式员工须提前 30 日书面通知；试用期员工提前 3 日。

实际：未调用生成

引用：无

人工结论：待复核

### HR-07 公司账号密码多久要换一次？

难度：easy ｜ 库：hr ｜ split：test

标注来源：信息安全与数据保密规范.md

检索来源：信息安全与数据保密规范.md, 关于启用新版考勤与请假制度的通知.md, 员工关系与假期常见问题 FAQ.md, hr-leave-quota-card.pdf, hr-travel-reimbursement-card.pdf

参考：每 90 天更换一次，且不得与前 5 次使用过的密码重复。

实际：未调用生成

引用：无

人工结论：待复核

### HR-08 签 3 年期限的劳动合同，试用期是多久？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：员工入职办理指南.md

检索来源：新员工试用期管理与转正流程.md, 员工入职办理指南.md, 病假管理与医疗期说明.md, 员工关系与假期常见问题 FAQ.md, 员工关系与假期常见问题 FAQ.md

参考：试用期为 3 个月，试用期工资按定薪的 90% 发放。

实际：未调用生成

引用：无

人工结论：待复核

### HR-09 我早上晚打卡了十几分钟，会被扣多少钱？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：考勤管理与打卡规范.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 日常费用报销管理办法.md, 关于启用新版考勤与请假制度的通知.md

参考：迟到 30 分钟以内每次扣发当月工资 50 元；超过 30 分钟按事假半天计。

实际：未调用生成

引用：无

人工结论：待复核

### HR-10 忘记打卡的话，一个月最多能补几次？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：考勤管理与打卡规范.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 关于启用新版考勤与请假制度的通知.md, 考勤管理与打卡规范.md, 关于启用新版考勤与请假制度的通知.md

参考：每月最多补卡 3 次，须在事发后 24 小时内提交。

实际：未调用生成

引用：无

人工结论：待复核

### HR-11 以前那份差旅住宿标准是不是作废了？现在按哪个文件执行？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：关于调整 2026 年度差旅住宿标准的通知.md

检索来源：关于调整 2026 年度差旅住宿标准的通知.md, 关于调整 2026 年度差旅住宿标准的通知.md, 差旅报销标准（其他城市）.md, 已废止制度清单与替代关系说明.md, 已废止制度清单与替代关系说明.md

参考：《差旅报销标准（2024 版）》自 2026 年 1 月 1 日起废止，现行以《差旅报销标准（一线城市）》与《差旅报销标准（其他城市）》为准。

实际：未调用生成

引用：无

人工结论：待复核

### HR-12 我们部门团建一年人均能花多少钱？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：餐饮与团建费用报销口径.md

检索来源：餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md, 节日福利与团建经费管理办法.md

参考：每人每季度 200 元，全年每人累计不超过 800 元。

实际：未调用生成

引用：无

人工结论：待复核

### HR-13 我每年买办公用品的预算是多少？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：办公用品采购与报销标准.md

检索来源：办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 报销与出差常见问题 FAQ.md

参考：1200 元/人，超出部分须部门负责人审批。

实际：未调用生成

引用：无

人工结论：待复核

### HR-14 周末值班能不能像加班那样换成调休？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：值班与加班补贴说明.md

检索来源：值班与加班补贴说明.md, 值班与加班补贴说明.md, 加班与调休管理办法.md, 加班与调休管理办法.md, 值班与加班补贴说明.md

参考：不能。值班只发补贴，休息日值班 300 元/次，不折算调休；只有被认定为加班的部分才能按倍数折算调休。

实际：未调用生成

引用：无

人工结论：待复核

### HR-15 绩效评级里拿 S 的人大概占多少比例？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：绩效考核管理办法.md

检索来源：绩效考核管理办法.md, 绩效考核管理办法.md, 绩效评级与结果应用说明.md, 绩效考核管理办法.md, 绩效评级与结果应用说明.md

参考：S 级 10%，A 级 25%，B 级 50%，C 级 12%，D 级 3%。

实际：未调用生成

引用：无

人工结论：待复核

### HR-16 连续两个季度评 D 会有什么后果？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：绩效评级与结果应用说明.md

检索来源：绩效评级与结果应用说明.md, 绩效评级与结果应用说明.md, 绩效考核管理办法.md, 绩效考核管理办法.md, 绩效考核管理办法.md

参考：进入为期 3 个月的绩效改进计划（PIP）。

实际：未调用生成

引用：无

人工结论：待复核

### HR-17 竞业限制一般要持续多久？补偿怎么算？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：离职证明与竞业限制说明.md

检索来源：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 日常费用报销管理办法.md, 绩效考核管理办法.md

参考：期限最长不超过 12 个月；补偿为离职前 12 个月平均工资的 30%，按月发放。

实际：未调用生成

引用：无

人工结论：待复核

### HR-18 提交申诉后多久能拿到结果？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：员工申诉与投诉处理流程.md

检索来源：员工申诉与投诉处理流程.md, 员工申诉与投诉处理流程.md, 绩效考核管理办法.md, 员工关系与假期常见问题 FAQ.md, 员工申诉与投诉处理流程.md

参考：受理时限 3 个工作日，自受理之日起 15 个工作日内给出书面结论。

实际：未调用生成

引用：无

人工结论：待复核

### HR-19 去上海出差，住宿一晚最多能报销多少钱？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：差旅报销标准（一线城市）.md

检索来源：差旅报销标准（一线城市）.md, 报销与出差常见问题 FAQ.md, 差旅报销标准（一线城市）.md, 差旅报销标准（一线城市）.md, 差旅报销标准（其他城市）.md

参考：600 元/晚，据实报销，超出部分由员工自理。

实际：未调用生成

引用：无

人工结论：待复核

### HR-20 去成都出差，住宿每晚的上限是多少？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：差旅报销标准（其他城市）.md

检索来源：关于调整 2026 年度差旅住宿标准的通知.md, 差旅报销标准（其他城市）.md, 差旅报销标准（一线城市）.md, 关于调整 2026 年度差旅住宿标准的通知.md, 报销与出差常见问题 FAQ.md

参考：450 元/晚。

实际：未调用生成

引用：无

人工结论：待复核

### HR-21 我在公司干了 6 年，年假能有几天？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：请假类型与假期额度对照表.md

检索来源：员工关系与假期常见问题 FAQ.md, 请假与休假管理制度.md, 请假类型与假期额度对照表.md, 请假类型与假期额度对照表.md, 病假管理与医疗期说明.md

参考：15 天。

实际：未调用生成

引用：无

人工结论：待复核

### HR-22 病假超过 5 天以后，工资按几成发？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：请假类型与假期额度对照表.md

检索来源：病假管理与医疗期说明.md, 病假管理与医疗期说明.md, 病假管理与医疗期说明.md, 病假管理与医疗期说明.md, 请假类型与假期额度对照表.md

参考：超出 5 天的部分按本人日工资的 60% 计发。

实际：未调用生成

引用：无

人工结论：待复核

### HR-23 加班换来的调休多久不用就会作废？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：加班与调休管理办法.md

检索来源：加班与调休管理办法.md, 加班与调休管理办法.md, 加班与调休管理办法.md, 加班与调休管理办法.md, 关于启用新版考勤与请假制度的通知.md

参考：自加班发生之日起 6 个月，逾期自动作废，不予折现。

实际：未调用生成

引用：无

人工结论：待复核

### HR-24 一笔 4800 元的差旅报销要走谁的审批？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：费用报销审批权限表.md

检索来源：费用报销审批权限表.md, 费用报销审批权限表.md, 费用报销审批权限表.md, 报销与出差常见问题 FAQ.md, 费用报销审批权限表.md

参考：属 1000 元（含）至 5000 元档，由直属主管与部门负责人审批。

实际：未调用生成

引用：无

人工结论：待复核

### HR-25 我们部门要添置一套约 3 万元的测试设备，审批流程要走到哪一级？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：采购与付款审批权限表.md

检索来源：采购与付款审批权限表.md, 报销与出差常见问题 FAQ.md, 采购与付款审批权限表.md, 办公用品采购与报销标准.md, 采购与付款审批权限表.md

参考：属 5000 元（含）至 50000 元档，由部门负责人、采购负责人与财务负责人审批。

实际：未调用生成

引用：无

人工结论：待复核

### HR-26 2026 年社保缴费基数的上下限是多少？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：社会保险与住房公积金管理办法.md

检索来源：社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 已废止制度清单与替代关系说明.md, 关于调整 2026 年度差旅住宿标准的通知.md

参考：上限 35283 元/月，下限 6821 元/月。

实际：未调用生成

引用：无

人工结论：待复核

### HR-27 P6 员工的年终奖基数是几个月工资？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：年终奖与绩效奖金发放办法.md

检索来源：年终奖与绩效奖金发放办法.md, 年终奖与绩效奖金发放办法.md, 年终奖与绩效奖金发放办法.md, 绩效评级与结果应用说明.md, 职级体系与薪资带宽表.md

参考：2 个月固定薪资。

实际：未调用生成

引用：无

人工结论：待复核

### HR-28 转正评估一般是什么时候启动？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：新员工试用期管理与转正流程.md

检索来源：新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 绩效考核管理办法.md, 晋升与调岗管理办法.md

参考：试用期届满前 10 个工作日启动转正评估。

实际：未调用生成

引用：无

人工结论：待复核

### HR-29 去上海出差 3 天 2 晚，补贴和住宿分别按什么标准算？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：出差管理办法.md, 差旅报销标准（一线城市）.md

检索来源：差旅报销标准（一线城市）.md, 出差管理办法.md, 出差管理办法.md, 报销与出差常见问题 FAQ.md, 关于调整 2026 年度差旅住宿标准的通知.md

参考：出差补贴 150 元/天（出发与返回当日各按半天计）；住宿上限 600 元/晚据实报销。两份文件各提供一半口径。

实际：未调用生成

引用：无

人工结论：待复核

### HR-30 年假没休完能折成钱吗？在职和离职有区别吗？

难度：multi_source ｜ 库：hr ｜ split：test

标注来源：请假与休假管理制度.md, 请假类型与假期额度对照表.md

检索来源：年终奖与绩效奖金发放办法.md, 请假与休假管理制度.md, 离职管理与工作交接流程.md, 离职管理与工作交接流程.md, 请假类型与假期额度对照表.md

参考：在职员工可在次年 3 月 31 日前申请折现，每年最多 5 天；离职时当年度应休未休年假按日工资 100% 折现，同样最多 5 天。

实际：未调用生成

引用：无

人工结论：待复核

### HR-31 加班到晚上十一点打车回家，这笔钱怎么报？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：加班与调休管理办法.md, 日常费用报销管理办法.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 差旅报销标准（其他城市）.md, 餐饮与团建费用报销口径.md, 报销与出差常见问题 FAQ.md

参考：加班至 22:00 之后可据实报销当日自公司至居住地的打车费，单次上限 120 元。

实际：未调用生成

引用：无

人工结论：待复核

### HR-32 试用期员工的绩效考核和转正评估分别怎么安排？

难度：multi_source ｜ 库：hr ｜ split：test

标注来源：新员工试用期管理与转正流程.md, 绩效考核管理办法.md

检索来源：新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 绩效考核管理办法.md, 绩效考核管理办法.md

参考：入职不满 2 个月不参与当季季度考核；转正评估单独使用《转正评估表》，在试用期届满前 10 个工作日启动。

实际：未调用生成

引用：无

人工结论：待复核

### HR-33 我要离职了，交接和竞业限制分别有什么要求？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：离职管理与工作交接流程.md, 离职证明与竞业限制说明.md

检索来源：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 离职管理与工作交接流程.md, 离职证明与竞业限制说明.md, 离职管理与工作交接流程.md

参考：正式员工须提前 30 日书面通知并完成工作交接；竞业限制只有在劳动合同或专项协议中明确约定才适用，未约定则不适用。

实际：未调用生成

引用：无

人工结论：待复核

### HR-34 一张 26000 元的差旅报销单要走到哪一级审批？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：费用报销审批权限表.md, 差旅报销标准（一线城市）.md

检索来源：费用报销审批权限表.md, 费用报销审批权限表.md, 费用报销审批权限表.md, 报销与出差常见问题 FAQ.md, 费用报销审批权限表.md

参考：单笔 20000 元（含）以上，须由分管副总、财务负责人与总经理审批。

实际：未调用生成

引用：无

人工结论：待复核

### HR-35 公司有没有员工期权或股权激励计划？行权价格怎么定？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：职级体系与薪资带宽表.md, 年终奖与绩效奖金发放办法.md, 绩效考核管理办法.md, 节日福利与团建经费管理办法.md, 年终奖与绩效奖金发放办法.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-36 员工的子女教育补贴标准是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：节日福利与团建经费管理办法.md, 职级体系与薪资带宽表.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md, 年终奖与绩效奖金发放办法.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-37 公司有没有通勤班车？班车路线和发车时间是怎么规定的？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：星桥科技员工手册（总则）.md, 考勤管理与打卡规范.md, 弹性工作制实施细则.md, 考勤管理与打卡规范.md, 日常费用报销管理办法.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-38 公司提供员工宿舍或者住房补贴吗？标准是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：报销与出差常见问题 FAQ.md, 员工入职办理指南.md, 节日福利与团建经费管理办法.md, 社会保险与住房公积金管理办法.md, 职级体系与薪资带宽表.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-39 常驻海外的派驻补贴标准是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：出差管理办法.md, 出差管理办法.md, 出差管理办法.md, 关于调整 2026 年度差旅住宿标准的通知.md, 报销与出差常见问题 FAQ.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-40 公司有企业年金计划吗？缴费比例是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：社会保险与住房公积金管理办法.md, 补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-41 员工购车补贴和油卡福利怎么申请？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：节日福利与团建经费管理办法.md, 星桥科技员工手册（总则）.md, 日常费用报销管理办法.md, 报销与出差常见问题 FAQ.md, 补充医疗保险与年度体检福利说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-42 公司有没有托育服务或母婴室？使用规则是什么？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：请假与休假管理制度.md, 星桥科技员工手册（总则）.md, 请假与休假管理制度.md, 关于启用新版考勤与请假制度的通知.md, 社会保险与住房公积金管理办法.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-43 弹性福利自选平台的积分额度是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：关于启用新版考勤与请假制度的通知.md, 节日福利与团建经费管理办法.md, 弹性工作制实施细则.md, 职级体系与薪资带宽表.md, 节日福利与团建经费管理办法.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-44 员工内部创业和项目孵化支持政策是怎么规定的？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：节日福利与团建经费管理办法.md, 培训管理办法.md, 节日福利与团建经费管理办法.md, 星桥科技员工手册（总则）.md, 弹性工作制实施细则.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-45 生育津贴的具体计算公式是什么？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：年终奖与绩效奖金发放办法.md, 请假类型与假期额度对照表.md, 餐饮与团建费用报销口径.md, 职级体系与薪资带宽表.md, 绩效评级与结果应用说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-46 加班超过每月 36 小时上限后，具体的处罚金额是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：加班与调休管理办法.md, 加班与调休管理办法.md, 职级体系与薪资带宽表.md, 值班与加班补贴说明.md, 已废止制度清单与替代关系说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-47 竞业限制违约金的计算基数是哪个月的工资？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 职级体系与薪资带宽表.md, 年终奖与绩效奖金发放办法.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-48 年度调薪的最终百分比由谁审批确定？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：绩效评级与结果应用说明.md, 职级体系与薪资带宽表.md, 绩效评级与结果应用说明.md, 绩效考核管理办法.md, 薪酬结构与发薪日历说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-49 体检报告异常后的复查费用能报销多少比例？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md, 报销与出差常见问题 FAQ.md, 补充医疗保险与年度体检福利说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-50 申诉调查中引入外部顾问的费用上限是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：员工申诉与投诉处理流程.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md, 采购与付款审批权限表.md, 员工关系与假期常见问题 FAQ.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### HR-51 IT 部门一位同事问：标准工时下的上班打卡有效窗口是几点到几点？

难度：cross_kb ｜ 库：hr ｜ split：dev

标注来源：（期望拒答）

检索来源：VPN 使用指南（北京）.md, 办公终端配置标准.md, 办公终端配置标准.md, 无线网络接入与访客 Wi-Fi 管理办法.md, 终端安全检查与补丁管理规范.md

参考：上班打卡有效窗口为 08:30 至 10:00，10:00 之后视为迟到。

实际：未调用生成

引用：无

人工结论：待复核

### HR-52 IT 运维同事问：周末值班的补贴标准是多少？

难度：cross_kb ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：VPN 使用指南（北京）.md, 数据备份策略与恢复演练规范.md, Wi-Fi 认证方式升级通知.md, Wi-Fi 认证方式升级通知.md, 打印机安装与驱动配置手册.md

参考：休息日值班 300 元/次，不折算调休。

实际：未调用生成

引用：无

人工结论：待复核

### HR-53 IT 部门 HRBP 咨询：员工每年带薪病假有几天？

难度：cross_kb ｜ 库：hr ｜ split：dev

标注来源：（期望拒答）

检索来源：数据备份策略与恢复演练规范.md, 终端设备领用与归还登记表.md, 权限申请与最小权限矩阵.md, 数据备份策略与恢复演练规范.md, IT 系统变更与版本记录.md

参考：每年 5 天带薪病假，超出部分按本人日工资的 60% 计发。

实际：未调用生成

引用：无

人工结论：待复核

### HR-54 产品经理问：去杭州出差住宿每晚最多能报销多少？

难度：cross_kb ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议常见问题 FAQ.md, 星桥会议常见问题 FAQ.md, 星桥科技服务等级协议 SLA 总则.md, 星桥科技统一计费与续费口径说明.md, 星桥会议套餐配额与并发说明.md

参考：450 元/晚（杭州属于其他城市）。

实际：未调用生成

引用：无

人工结论：待复核

### HR-55 产品团队同事问：婚假有多少天？

难度：cross_kb ｜ 库：hr ｜ split：dev

标注来源：（期望拒答）

检索来源：星桥工单 SLA 分级与响应时限.md, 星桥云盘数据备份与保留策略.md, 星桥会议接口接入与鉴权指南.md, 星桥云盘开放接口接入指南.md, 星桥会议录制与存储保留策略.md

参考：婚假 10 个自然日，须在领证之日起 12 个月内休完。

实际：未调用生成

引用：无

人工结论：待复核

### HR-56 产品部门问：团建经费每人每季度是多少钱？

难度：cross_kb ｜ 库：hr ｜ split：dev

标注来源：（期望拒答）

检索来源：星桥科技统一计费与续费口径说明.md, 星桥会议套餐配额与并发说明.md, 星桥会议套餐配额与并发说明.md, 星桥云盘套餐与配额对照表.md, 星桥云盘套餐与配额对照表.md

参考：每人每季度 200 元，全年每人累计不超过 800 元。

实际：未调用生成

引用：无

人工结论：待复核

### IT-01 公司 IT 服务台的分机号是多少？

难度：easy ｜ 库：it ｜ split：test

标注来源：VPN 使用指南（北京）.md

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, 打印机安装与驱动配置手册.md, VPN 客户端故障排查清单.md, 密码找回与重置流程 FAQ.md, 邮件误发与撤回应急处理指引.md

参考：分机 6001。

实际：未调用生成

引用：无

人工结论：待复核

### IT-02 连接内网时客户端报错误码 691，一般是哪里出了问题？

难度：easy ｜ 库：it ｜ split：dev

标注来源：VPN 客户端故障排查清单.md

检索来源：办公网络端口与服务清单.md, VPN 客户端故障排查清单.md, 无线信号弱与频繁掉线排查清单.md, 办公网络端口与服务清单.md, 无线信号弱与频繁掉线排查清单.md

参考：用户名或密码错误，需要核对凭据的大小写与输入法。

实际：未调用生成

引用：无

人工结论：待复核

### IT-03 协同盘里被删掉的文件在回收站能放多久？

难度：easy ｜ 库：it ｜ split：dev

标注来源：共享盘目录结构与权限规范.md

检索来源：共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md

参考：回收站保留 30 天。

实际：未调用生成

引用：无

人工结论：待复核

### IT-04 来访客户用的 Wi-Fi 通行码能用多长时间？

难度：easy ｜ 库：it ｜ split：test

标注来源：无线网络接入与访客 Wi-Fi 管理办法.md

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, 无线网络接入与访客 Wi-Fi 管理办法.md, 无线网络接入与访客 Wi-Fi 管理办法.md, VPN 使用指南（北京）.md, VPN 使用指南（上海）.md

参考：通行码有效期 6 小时，过期不延期。

实际：未调用生成

引用：无

人工结论：待复核

### IT-05 打印黑白单面一页要收多少钱？

难度：easy ｜ 库：it ｜ split：dev

标注来源：打印计费与耗材申领规定.md

检索来源：打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印机安装与驱动配置手册.md, 打印机安装与驱动配置手册.md

参考：黑白单面 0.05 元/页。

实际：未调用生成

引用：无

人工结论：待复核

### IT-06 发现信息安全事件时的应急电话是多少？

难度：easy ｜ 库：it ｜ split：dev

标注来源：信息安全事件分级与上报流程.md

检索来源：信息安全事件分级与上报流程.md, 邮件误发与撤回应急处理指引.md, 信息安全事件分级与上报流程.md, 信息安全事件分级与上报流程.md, 密码找回与重置流程 FAQ.md

参考：分机 6001，全年可拨。

实际：未调用生成

引用：无

人工结论：待复核

### IT-07 新员工入职后的域账号一般多久能开通好？

难度：easy ｜ 库：it ｜ split：test

标注来源：AD 域账号与权限管理规定.md

检索来源：AD 域账号与权限管理规定.md, 密码找回与重置流程 FAQ.md, 域账号锁定与解锁自助指南.md, AD 域账号与权限管理规定.md, 域账号锁定与解锁自助指南.md

参考：收到入职名单后 4 小时内完成主账号创建。

实际：未调用生成

引用：无

人工结论：待复核

### IT-08 会议室屏幕上显示的投屏码多久会失效？

难度：easy ｜ 库：it ｜ split：dev

标注来源：会议室音视频设备使用手册.md

检索来源：会议室音视频设备使用手册.md, 会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md, 会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md

参考：投屏码有效期 2 分钟，超时需重新获取。

实际：未调用生成

引用：无

人工结论：待复核

### IT-09 手机上那个每次刷新的动态数字，连续输错会被停多久？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：多因素认证（MFA）操作手册.md

检索来源：多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, Wi-Fi 认证方式升级通知.md, 域账号锁定与解锁自助指南.md, Wi-Fi 认证方式升级通知.md

参考：连续 5 次错误会锁定 10 分钟。

实际：未调用生成

引用：无

人工结论：待复核

### IT-10 在北京家里办公时，一次远程连接最长能挂多久就必须重新认证？

难度：paraphrase ｜ 库：it ｜ split：test

标注来源：VPN 使用指南（北京）.md

检索来源：VPN 使用指南（北京）.md, Wi-Fi 认证方式升级通知.md, 远程接入与零信任管理办法.md, 远程接入与零信任管理办法.md, 域账号锁定与解锁自助指南.md

参考：单次连接最长 8 小时，达到后自动断开。

实际：未调用生成

引用：无

人工结论：待复核

### IT-11 华东区同事走上海通道，单次连接可以连续用多长时间？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：VPN 使用指南（上海）.md

检索来源：VPN 使用指南（上海）.md, VPN 使用指南（上海）.md, 远程接入与零信任管理办法.md, VPN 使用指南（北京）.md, VPN 使用指南（上海）.md

参考：单次连接最长 12 小时。

实际：未调用生成

引用：无

人工结论：待复核

### IT-12 发邮件时最多能带多大的附件？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：企业邮箱使用手册.md

检索来源：企业邮箱容量与附件限制说明.md, 企业邮箱容量与附件限制说明.md, 企业邮箱使用手册.md, 企业邮箱容量与附件限制说明.md, 扫描到邮箱与共享盘操作指南.md

参考：单封邮件附件累计不超过 25 MB。

实际：未调用生成

引用：无

人工结论：待复核

### IT-13 内部邮件发错人了，还能在多长时间内点撤回？

难度：paraphrase ｜ 库：it ｜ split：test

标注来源：邮件误发与撤回应急处理指引.md

检索来源：邮件误发与撤回应急处理指引.md, 邮件误发与撤回应急处理指引.md, 邮件误发与撤回应急处理指引.md, 密码复杂度与锁定策略规范.md, 企业邮箱容量与附件限制说明.md

参考：内部邮件撤回窗口为发出后 2 分钟内，外部邮件不支持撤回。

实际：未调用生成

引用：无

人工结论：待复核

### IT-14 打印完忘了拿，材料会在机器里留多久？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：打印机安装与驱动配置手册.md

检索来源：打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 终端设备领用与归还登记表.md

参考：打印任务保留 2 小时，超时自动清除。

实际：未调用生成

引用：无

人工结论：待复核

### IT-15 往公司外面发文件，超过多大就得先让部门负责人点头？

难度：paraphrase ｜ 库：it ｜ split：test

标注来源：文件协作与外发审批办法.md

检索来源：文件协作与外发审批办法.md, 文件协作与外发审批办法.md, 文件协作与外发审批办法.md, 扫描到邮箱与共享盘操作指南.md, 企业邮箱使用手册.md

参考：外发文件超过 50 MB 需部门负责人审批。

实际：未调用生成

引用：无

人工结论：待复核

### IT-16 公司配的笔记本，电池至少要能撑多久才算达标？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：办公终端配置标准.md

检索来源：办公终端配置标准.md, 办公终端配置标准.md, 办公终端配置标准.md, 终端设备领用与归还登记表.md, 终端安全检查与补丁管理规范.md

参考：电池续航不低于 6 小时。

实际：未调用生成

引用：无

人工结论：待复核

### IT-17 客户名单这种材料想直接打印出来，要先办什么手续？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：打印机安装与驱动配置手册.md

检索来源：打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md, 常用软件自助安装指引.md, 打印计费与耗材申领规定.md, 打印机安装与驱动配置手册.md

参考：必须先走《文件协作与外发审批办法》，禁止直接打印客户名单。

实际：未调用生成

引用：无

人工结论：待复核

### IT-18 换了新手机以后，令牌绑定要在多长时间内弄完？

难度：paraphrase ｜ 库：it ｜ split：test

标注来源：多因素认证（MFA）操作手册.md

检索来源：多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, Wi-Fi 认证方式升级通知.md, 密码找回与重置流程 FAQ.md

参考：新手机绑定需 30 分钟内完成扫码与验证。

实际：未调用生成

引用：无

人工结论：待复核

### IT-19 域账号密码连续输错几次会被锁？锁多久？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：域账号锁定与解锁自助指南.md

检索来源：域账号锁定与解锁自助指南.md, 域账号锁定与解锁自助指南.md, 密码找回与重置流程 FAQ.md, 密码复杂度与锁定策略规范.md, 域账号锁定与解锁自助指南.md

参考：连续 6 次密码错误锁定 15 分钟，到期自动解锁。

实际：未调用生成

引用：无

人工结论：待复核

### IT-20 邮箱密码连续输错几次会锁？锁上之后能自己等到解锁吗？

难度：numeric ｜ 库：it ｜ split：test

标注来源：企业邮箱使用手册.md

检索来源：密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md, 账号锁定与解锁自助指南.md, 域账号锁定与解锁自助指南.md, 域账号锁定与解锁自助指南.md

参考：连续 3 次锁定，且不设自动解锁时长，需致电服务台人工解锁。

实际：未调用生成

引用：无

人工结论：待复核

### IT-21 无线网络认证连续失败几次会被临时挡住？挡多长时间？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：无线网络接入与访客 Wi-Fi 管理办法.md

检索来源：Wi-Fi 认证方式升级通知.md, 无线信号弱与频繁掉线排查清单.md, 无线信号弱与频繁掉线排查清单.md, Wi-Fi 认证方式升级通知.md, 多因素认证（MFA）操作手册.md

参考：连续 4 次认证失败锁定 20 分钟，到期自动解锁。

实际：未调用生成

引用：无

人工结论：待复核

### IT-22 公司对密码长度最低要求是多少位？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：密码复杂度与锁定策略规范.md

检索来源：密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md, VPN 使用指南（上海）.md, 密码复杂度与锁定策略规范.md

参考：长度不少于 12 位。

实际：未调用生成

引用：无

人工结论：待复核

### IT-23 员工主账号的密码多久必须换一次？

难度：numeric ｜ 库：it ｜ split：test

标注来源：密码复杂度与锁定策略规范.md

检索来源：密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md, 密码找回与重置流程 FAQ.md, 密码复杂度与锁定策略规范.md, 密码找回与重置流程 FAQ.md

参考：每 90 天更换一次。

实际：未调用生成

引用：无

人工结论：待复核

### IT-24 公司邮箱给正式员工分配多少容量？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：企业邮箱容量与附件限制说明.md

检索来源：企业邮箱使用手册.md, 企业邮箱容量与附件限制说明.md, 企业邮箱容量与附件限制说明.md, 企业邮箱使用手册.md, 企业邮箱容量与附件限制说明.md

参考：正式员工邮箱容量 50 GB。

实际：未调用生成

引用：无

人工结论：待复核

### IT-25 全量备份和增量备份分别保留多久？

难度：numeric ｜ 库：it ｜ split：test

标注来源：数据备份策略与恢复演练规范.md

检索来源：数据备份策略与恢复演练规范.md, 数据备份策略与恢复演练规范.md, 共享盘目录结构与权限规范.md, IT 系统变更与版本记录.md, 文件误删恢复申请指引.md

参考：全量保留 8 周，增量保留 30 天。

实际：未调用生成

引用：无

人工结论：待复核

### IT-26 高危补丁要求在多长时间内装完？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：终端安全检查与补丁管理规范.md

检索来源：终端安全检查与补丁管理规范.md, 终端安全检查与补丁管理规范.md, 办公终端配置标准.md, 远程接入与零信任管理办法.md, 软件安装申请与审批流程.md

参考：发布后 72 小时内完成。

实际：未调用生成

引用：无

人工结论：待复核

### IT-27 个人办公终端默认的下行限速是多少？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：网络带宽使用与限速规定.md

检索来源：网络带宽使用与限速规定.md, VPN 使用指南（北京）.md, 网络带宽使用与限速规定.md, 办公终端配置标准.md, 网络带宽使用与限速规定.md

参考：个人终端默认下行限速 100 Mbps。

实际：未调用生成

引用：无

人工结论：待复核

### IT-28 彩色打印一页收多少钱？

难度：numeric ｜ 库：it ｜ split：test

标注来源：打印计费与耗材申领规定.md

检索来源：打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印机安装与驱动配置手册.md, 打印机安装与驱动配置手册.md

参考：彩色单面 0.35 元/页。

实际：未调用生成

引用：无

人工结论：待复核

### IT-29 我在家想打开部门共享盘，网络连上以外还差什么条件？

难度：multi_source ｜ 库：it ｜ split：test

标注来源：远程接入与零信任管理办法.md, 共享盘目录结构与权限规范.md

检索来源：共享盘目录结构与权限规范.md, 有线接入与交换机端口登记表.md, 无线信号弱与频繁掉线排查清单.md, 办公网络端口与服务清单.md, 企业邮箱使用手册.md

参考：需通过零信任设备合规检查，且部门目录默认已按部门授权；跨部门项目目录需项目负责人提交成员名单。

实际：未调用生成

引用：无

人工结论：待复核

### IT-30 密码忘了、手机令牌也不能用，人工重置要核验什么？临时密码能活多久？

难度：multi_source ｜ 库：it ｜ split：dev

标注来源：密码找回与重置流程 FAQ.md, 多因素认证（MFA）操作手册.md

检索来源：密码找回与重置流程 FAQ.md, 多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, 密码找回与重置流程 FAQ.md

参考：先致电 6001 冻结令牌，再完成身份核验（工牌或工号、预留手机号、主管确认任两项）；核验后发放临时密码，有效期 2 小时且首次登录必须修改。

实际：未调用生成

引用：无

人工结论：待复核

### IT-31 用一体机扫描的文件默认发到哪？太大发不出去怎么办？

难度：multi_source ｜ 库：it ｜ split：test

标注来源：扫描到邮箱与共享盘操作指南.md, 企业邮箱容量与附件限制说明.md

检索来源：扫描到邮箱与共享盘操作指南.md, 扫描到邮箱与共享盘操作指南.md, 扫描到邮箱与共享盘操作指南.md, 扫描到邮箱与共享盘操作指南.md, 打印机安装与驱动配置手册.md

参考：默认发送至本人企业邮箱；超过 25 MB 时邮件系统提示改用超大附件链接。

实际：未调用生成

引用：无

人工结论：待复核

### IT-32 员工离职时，账号和办公电脑分别在什么时候处理完？

难度：multi_source ｜ 库：it ｜ split：dev

标注来源：离职与转岗账号回收流程.md, 终端设备领用与归还登记表.md

检索来源：离职与转岗账号回收流程.md, 离职与转岗账号回收流程.md, 离职与转岗账号回收流程.md, 离职与转岗账号回收流程.md, 终端设备领用与归还登记表.md

参考：账号在离职当日 18:00 前禁用并完成令牌注销与 VPN 权限回收；办公终端最迟在离职后 5 个工作日内归还。

实际：未调用生成

引用：无

人工结论：待复核

### IT-33 会议开到一半投屏断了，按文档应该怎么应急？

难度：multi_source ｜ 库：it ｜ split：dev

标注来源：会议室音视频设备使用手册.md, 会议室预约与设备故障报备 FAQ.md

检索来源：会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md, 会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md, 无线信号弱与频繁掉线排查清单.md

参考：改用有线连接作为应急方案；必要时断电重启投屏器并致电 6001 申请调换会议室。

实际：未调用生成

引用：无

人工结论：待复核

### IT-34 协同盘里的文件被误删，回收站也已经过期，还能从哪里找回？

难度：multi_source ｜ 库：it ｜ split：test

标注来源：文件误删恢复申请指引.md, 数据备份策略与恢复演练规范.md

检索来源：文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 共享盘目录结构与权限规范.md, 共享盘目录结构与权限规范.md

参考：删除超过 30 天需由系统与账号组从备份副本恢复；一级系统另有保留 90 天的异地副本。

实际：未调用生成

引用：无

人工结论：待复核

### IT-35 星桥科技员工每年能休多少天年假？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：AD 域账号与权限管理规定.md, 办公终端配置标准.md, 权限申请与最小权限矩阵.md, IT 系统变更与版本记录.md, 密码复杂度与锁定策略规范.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-36 公司今年春节的放假安排是怎么定的？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：it-exit-account-revocation.pdf, 密码复杂度与锁定策略规范.md, 日历共享与会议室预订 FAQ.md, 数据备份策略与恢复演练规范.md, it-vpn-lockout-policy.pdf

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-37 公司提供餐补吗？食堂几点开饭？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：Wi-Fi 认证方式升级通知.md, 会议室预约与设备故障报备 FAQ.md, 会议室预约与设备故障报备 FAQ.md, 无线网络接入与访客 Wi-Fi 管理办法.md, 打印机安装与驱动配置手册.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-38 办公楼停车位是怎么收费的？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：打印机安装与驱动配置手册.md, 日历共享与会议室预订 FAQ.md, 办公终端配置标准.md, 软件安装申请与审批流程.md, 有线接入与交换机端口登记表.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-39 公司健身房每天开放到几点？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：VPN 使用指南（北京）.md, 会议室预约与设备故障报备 FAQ.md, Wi-Fi 认证方式升级通知.md, VPN 使用指南（北京）.md, 日历共享与会议室预订 FAQ.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-40 星桥科技的股票期权行权价格是多少？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：正版软件授权与 License 台账.md, AD 域账号与权限管理规定.md, 密码复杂度与锁定策略规范.md, 办公终端配置标准.md, 网络带宽使用与限速规定.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-41 公司给供应商付款的账期是多少天？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：正版软件授权与 License 台账.md, 终端设备领用与归还登记表.md, 数据备份策略与恢复演练规范.md, 文件协作与外发审批办法.md, 打印计费与耗材申领规定.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-42 出差住宿费的报销上限是多少？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, VPN 使用指南（北京）.md, VPN 使用指南（上海）.md, 日历共享与会议室预订 FAQ.md, 无线网络接入与访客 Wi-Fi 管理办法.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-43 星桥协同盘企业版对外售价是多少？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：共享盘目录结构与权限规范.md, 办公终端配置标准.md, 正版软件授权与 License 台账.md, 网络带宽使用与限速规定.md, 文件协作与外发审批办法.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-44 公司办公楼多久组织一次消防演练？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：数据备份策略与恢复演练规范.md, 数据备份策略与恢复演练规范.md, 会议室音视频设备使用手册.md, 无线信号弱与频繁掉线排查清单.md, Wi-Fi 认证方式升级通知.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-45 北京 VPN 节点使用的隧道加密算法是哪一种？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：远程接入与零信任管理办法.md, VPN 使用指南（北京）.md, 远程接入与零信任管理办法.md, VPN 使用指南（上海）.md, 多因素认证（MFA）操作手册.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-46 打印一体机使用的墨盒型号是什么？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：打印机安装与驱动配置手册.md, 打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md, 打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-47 公司根证书的有效期是几年？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：正版软件授权与 License 台账.md, 正版软件授权与 License 台账.md, AD 域账号与权限管理规定.md, 权限申请与最小权限矩阵.md, 正版软件授权与 License 台账.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-48 IT 服务台值班人员的名单和工号在哪里能查到？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, VPN 客户端故障排查清单.md, 办公网络端口与服务清单.md, 密码找回与重置流程 FAQ.md, 打印机安装与驱动配置手册.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-49 会议室摄像头的最大光学变焦倍数是多少？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md, 日历共享与会议室预订 FAQ.md, 会议室音视频设备使用手册.md, 扫描到邮箱与共享盘操作指南.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-50 共享盘单文件超过 5 GB 时，官方建议怎么拆分？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：共享盘目录结构与权限规范.md, 共享盘目录结构与权限规范.md, 扫描到邮箱与共享盘操作指南.md, 共享盘目录结构与权限规范.md, 扫描到邮箱与共享盘操作指南.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### IT-51 新人入职当天人事已经提报名单了，我这边邮箱多久能用上？

难度：cross_kb ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：员工入职办理指南.md, 员工入职办理指南.md, 员工关系与假期常见问题 FAQ.md, 员工入职办理指南.md, 用章与合同审批权限表.md

参考：收到名单后 4 小时内完成主账号创建，并同步开通邮箱与工单系统。

实际：未调用生成

引用：无

人工结论：待复核

### IT-52 员工离职当天，公司账号和相关权限什么时候停掉？

难度：cross_kb ｜ 库：it ｜ split：dev

标注来源：（期望拒答）

检索来源：离职管理与工作交接流程.md, 离职管理与工作交接流程.md, 离职管理与工作交接流程.md, 离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md

参考：离职当日 18:00 前完成账号禁用、令牌注销与 VPN 权限回收。

实际：未调用生成

引用：无

人工结论：待复核

### IT-53 实习生和外包驻场人员的账号最长能用到多久？

难度：cross_kb ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：新员工试用期管理与转正流程.md, 员工关系与假期常见问题 FAQ.md, 培训管理办法.md, 请假类型与假期额度对照表.md, 员工关系与假期常见问题 FAQ.md

参考：实习生账号最长 6 个月，外包驻场账号最长 3 个月。

实际：未调用生成

引用：无

人工结论：待复核

### IT-54 客户问协同盘个人空间有多大、单个文件能传多大？

难度：cross_kb ｜ 库：it ｜ split：dev

标注来源：（期望拒答）

检索来源：星桥云盘账号与共享授权说明.md, 星桥会议与云盘集成说明.md, 星桥云盘数据导入导出操作指南.md, 星桥会议套餐配额与并发说明.md, 星桥云盘账号与共享授权说明.md

参考：个人目录配额 20 GB，单个文件不超过 5 GB。

实际：未调用生成

引用：无

人工结论：待复核

### IT-55 客户想了解会议室投屏，投屏码有效期是多久？

难度：cross_kb ｜ 库：it ｜ split：dev

标注来源：（期望拒答）

检索来源：星桥会议接口接入与鉴权指南.md, 星桥科技统一计费与续费口径说明.md, 星桥科技统一账号与单点登录说明.md, 星桥会议常见问题 FAQ.md, 星桥科技统一计费与续费口径说明.md

参考：投屏码有效期 2 分钟，超时需重新获取。

实际：未调用生成

引用：无

人工结论：待复核

### IT-56 客户问公司邮箱的附件上限，以及超大附件链接能挂多久？

难度：cross_kb ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单常见问题 FAQ.md, 星桥工单产品功能手册.md, 星桥云盘开放接口接入指南.md, 星桥云盘套餐与配额对照表.md, 星桥云盘产品功能手册.md

参考：单封邮件附件累计不超过 25 MB，超大附件链接有效期 14 天。

实际：未调用生成

引用：无

人工结论：待复核

### PD-01 我们往星桥云盘传一个 30 GB 的备份包一直失败，云盘单文件最大能到多少？

难度：easy ｜ 库：product ｜ split：test

标注来源：星桥云盘产品功能手册.md

检索来源：星桥云盘错误码说明.md, 星桥云盘产品功能手册.md, 星桥云盘套餐与配额对照表.md, 星桥云盘产品功能手册.md, 星桥云盘套餐与配额对照表.md

参考：单文件最大 20 GB；超过 200 MB 的文件会自动走分片上传，分片大小默认 8 MB，超过 20 GB 只能分卷压缩后重传。

实际：未调用生成

引用：无

人工结论：待复核

### PD-02 同事误删了云盘里的文件，回收站能放多久还能找回来？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥云盘产品功能手册.md

检索来源：星桥会议录制与存储保留策略.md, 星桥云盘数据备份与保留策略.md, 星桥会议录制与存储保留策略.md, 星桥云盘产品功能手册.md, 星桥云盘数据备份与保留策略.md

参考：删除的文件进入回收站后保留 30 天，普通成员可自助恢复；超过保留期进入清理队列，物理删除后无法找回。

实际：未调用生成

引用：无

人工结论：待复核

### PD-03 我们是基础版，星桥云盘的存储额度到底是多少？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥云盘套餐与配额对照表.md

检索来源：星桥云盘套餐与配额对照表.md, 星桥云盘套餐与配额对照表.md, 星桥云盘产品功能手册.md, 星桥会议常见问题 FAQ.md, 星桥会议套餐配额与并发说明.md

参考：基础版存储配额 100 GB，标准版 1 TB，旗舰版 5 TB；回收站与历史版本同样计入实际占用。

实际：未调用生成

引用：无

人工结论：待复核

### PD-04 用基础版开一场会议，最长能开多久？

难度：easy ｜ 库：product ｜ split：test

标注来源：星桥会议套餐配额与并发说明.md

检索来源：星桥会议常见问题 FAQ.md, 星桥会议常见问题 FAQ.md, 星桥会议套餐配额与并发说明.md, 星桥会议接口接入与鉴权指南.md, 星桥科技统一账号与单点登录说明.md

参考：基础版单场时长上限 40 分钟，达到上限会议自动结束，可立即重新发起；标准版与旗舰版单场最长 24 小时。

实际：未调用生成

引用：无

人工结论：待复核

### PD-05 工单里最多能挂多大的附件？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥工单产品功能手册.md

检索来源：星桥工单产品功能手册.md, 星桥工单产品功能手册.md, 星桥工单常见问题 FAQ.md, 星桥工单版本发布说明 v4.2.md, 星桥工单常见故障排查.md

参考：单个附件不超过 50 MB，单工单累计不超过 200 MB，超过会提示改用云盘链接。

实际：未调用生成

引用：无

人工结论：待复核

### PD-06 调用星桥会议接口拿到的令牌能用多长时间？

难度：easy ｜ 库：product ｜ split：test

标注来源：星桥会议接口接入与鉴权指南.md

检索来源：星桥会议接口接入与鉴权指南.md, 星桥科技统一账号与单点登录说明.md, 星桥工单接口鉴权与调用规范.md, 星桥科技统一账号与单点登录说明.md, 星桥科技统一账号与单点登录说明.md

参考：会议接口访问令牌有效期 24 小时，且不支持刷新令牌，过期后需要重新换取。

实际：未调用生成

引用：无

人工结论：待复核

### PD-07 星桥云盘开放接口的访问令牌有效期是几个小时？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥云盘开放接口接入指南.md

检索来源：星桥科技统一账号与单点登录说明.md, 星桥会议接口接入与鉴权指南.md, 星桥云盘开放接口接入指南.md, 星桥工单接口鉴权与调用规范.md, 星桥云盘账号与共享授权说明.md

参考：云盘访问令牌有效期 2 小时，刷新令牌有效期 30 天，且刷新令牌只能使用一次。

实际：未调用生成

引用：无

人工结论：待复核

### PD-08 星桥工单的接口令牌多久会过期？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥工单接口鉴权与调用规范.md

检索来源：星桥工单接口鉴权与调用规范.md, 星桥会议接口接入与鉴权指南.md, 星桥工单 4.x 迁移说明.md, 星桥科技统一账号与单点登录说明.md, 星桥科技统一账号与单点登录说明.md

参考：工单接口访问令牌有效期 1 小时，刷新令牌有效期 14 天。

实际：未调用生成

引用：无

人工结论：待复核

### PD-09 我们的上传脚本还在用老接口，官方说该换成哪个新接口了？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥云盘开放接口接入指南.md

检索来源：星桥会议 1.x 客户端停用公告.md, 星桥云盘开放接口接入指南.md, 星桥云盘开放接口接入指南.md, 星桥会议版本发布说明 v2.8.md, 星桥会议 1.x 客户端停用公告.md

参考：旧上传接口 POST /api/v2/files/upload 自 v3.0 起废弃，请改用 POST /api/v3/drive/objects；旧接口计划在 v3.6 停止服务。

实际：未调用生成

引用：无

人工结论：待复核

### PD-10 会议接口里的 room.create 还能继续用吗，应该换成什么？

难度：paraphrase ｜ 库：product ｜ split：test

标注来源：星桥会议接口接入与鉴权指南.md

检索来源：星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议版本发布说明 v2.8.md, 星桥会议接口接入与鉴权指南.md, 星桥会议接口接入与鉴权指南.md

参考：旧接口 room.create 自 v2.5 起废弃，请改用 rooms.create，REST 路径为 POST /api/v2/rooms。

实际：未调用生成

引用：无

人工结论：待复核

### PD-11 我们的集成里还在用 X-Legacy-Token 这个请求头，现在有替代做法吗？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥工单接口鉴权与调用规范.md

检索来源：星桥科技 API 通用错误码与重试规范.md, 星桥工单错误码与限流对照表.md, 星桥会议 1.x 客户端停用公告.md, 星桥工单 4.x 迁移说明.md, 星桥工单 4.x 迁移说明.md

参考：旧鉴权请求头 X-Legacy-Token 自 v4.1 起废弃，请改用标准 Bearer 令牌，且旧请求头不支持细粒度权限范围。

实际：未调用生成

引用：无

人工结论：待复核

### PD-12 客户端同步协议是不是换过了，旧协议还能不能用？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥云盘开放接口接入指南.md

检索来源：星桥云盘客户端兼容性矩阵.md, 星桥工单 4.x 迁移说明.md, 星桥云盘同步失败排查手册.md, 星桥会议 1.x 客户端停用公告.md, 星桥云盘套餐与配额对照表.md

参考：旧同步协议 sync-legacy 自 v3.2 起废弃，请改用 sync-v3，旧协议不再修复缺陷，冲突时只能后写覆盖。

实际：未调用生成

引用：无

人工结论：待复核

### PD-13 公司里几台老会议客户端一直提示版本过低登不上，是怎么回事？

难度：paraphrase ｜ 库：product ｜ split：test

标注来源：星桥会议 1.x 客户端停用公告.md

检索来源：星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议版本发布说明 v2.8.md

参考：星桥会议 1.x 桌面客户端自 v2.0 起已停用，请改用 2.x 客户端；过渡期已于 2026-07-19 结束，之后无法登录。

实际：未调用生成

引用：无

人工结论：待复核

### PD-14 工单邮件通知显示发送成功，但同事说收不到，通常卡在哪里？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥工单通知模板与回调配置.md

检索来源：星桥工单常见故障排查.md, 星桥工单常见故障排查.md, 星桥工单常见问题 FAQ.md, 星桥工单常见问题 FAQ.md, 星桥工单常见故障排查.md

参考：常见原因是企业防火墙只放通了 25 端口，邮件通道使用 2525 端口，未放通就会出现发送状态成功但用户收不到的假象。

实际：未调用生成

引用：无

人工结论：待复核

### PD-15 新入职的同事点提交工单没反应，一般是什么原因？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥工单常见问题 FAQ.md

检索来源：星桥工单常见问题 FAQ.md, 星桥工单常见故障排查.md, 星桥工单常见故障排查.md, 星桥工单提交与升级机制.md, 星桥工单 SLA 分级与响应时限.md

参考：常见原因有两个：账号未加入服务范围，或账号角色仅具备查看权限，需管理员在成员与服务范围中确认。

实际：未调用生成

引用：无

人工结论：待复核

### PD-16 怎么判断会议卡顿是网络问题还是产品本身的问题？

难度：paraphrase ｜ 库：product ｜ split：test

标注来源：星桥会议音视频质量排查指南.md

检索来源：星桥会议音视频质量排查指南.md, 星桥会议音视频质量排查指南.md, 星桥会议错误码速查表.md, 星桥会议音视频质量排查指南.md, 星桥会议错误码速查表.md

参考：先看网络诊断四项：丢包率低于 5%、抖动低于 30 毫秒、时延低于 200 毫秒、上行不低于 1.5 Mbps；四项合格仍卡顿再排查客户端性能。

实际：未调用生成

引用：无

人工结论：待复核

### PD-17 云盘客户端图标变成黄色感叹号，是不是文件全丢了？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥云盘同步失败排查手册.md

检索来源：星桥云盘同步失败排查手册.md, 星桥会议录制与存储保留策略.md, 星桥云盘产品功能手册.md, 星桥工单接口鉴权与调用规范.md, 星桥会议录制与存储保留策略.md

参考：黄色感叹号表示部分失败，不是全部丢失；应在客户端最近错误中查看错误码再决定处理动作。

实际：未调用生成

引用：无

人工结论：待复核

### PD-18 会议录制到底保留多久，是 90 天还是 30 天？

难度：paraphrase ｜ 库：product ｜ split：test

标注来源：星桥会议录制与存储保留策略.md

检索来源：星桥会议录制与存储保留策略.md, 星桥会议录制与存储保留策略.md, 星桥云盘数据备份与保留策略.md, 星桥会议录制与存储保留策略.md, 星桥会议与云盘集成说明.md

参考：两段叠加：标准版会议侧保留 90 天，到期移入云盘回收站再保留 30 天，从生成到彻底不可恢复最长约 120 天；旗舰版为 180 加 30 等于 210 天。

实际：未调用生成

引用：无

人工结论：待复核

### PD-19 云盘接口报 429 说并发超限，具体上限是几个？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥云盘错误码说明.md

检索来源：星桥云盘错误码说明.md, 星桥工单错误码与限流对照表.md, 星桥工单错误码与限流对照表.md, 星桥科技 API 通用错误码与重试规范.md, 星桥科技 API 通用错误码与重试规范.md

参考：星桥云盘的 429 只有一种成因：并发上传数超过 8 个，错误码为 UPLOAD_CONCURRENCY_EXCEEDED，应降低并发并按 1 秒、2 秒、4 秒退避重试。

实际：未调用生成

引用：无

人工结论：待复核

### PD-20 工单接口每分钟最多能调用多少次，超了会怎样？

难度：numeric ｜ 库：product ｜ split：test

标注来源：星桥工单错误码与限流对照表.md

检索来源：星桥工单接口鉴权与调用规范.md, 星桥工单常见故障排查.md, 星桥工单错误码与限流对照表.md, 星桥工单常见故障排查.md, 星桥工单产品功能手册.md

参考：工单接口限流为每令牌每分钟 120 次，采用 60 秒滑动窗口，超出返回 429 并在响应头给出 Retry-After。

实际：未调用生成

引用：无

人工结论：待复核

### PD-21 开会时提示会议室资源繁忙，对应的是哪个错误码？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥会议错误码速查表.md

检索来源：星桥会议错误码速查表.md, 星桥会议错误码速查表.md, 星桥会议错误码速查表.md, 星桥会议接口接入与鉴权指南.md, 星桥会议套餐配额与并发说明.md

参考：错误码为 ROOM_LICENSE_EXHAUSTED，含义是并发会议室许可已满，应结束闲置会议或申请临时扩容。

实际：未调用生成

引用：无

人工结论：待复核

### PD-22 星桥统一网关的总量限流阈值是多少，超了返回什么？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥科技 API 通用错误码与重试规范.md

检索来源：星桥科技 API 通用错误码与重试规范.md, 星桥工单错误码与限流对照表.md, 星桥云盘错误码说明.md, 星桥工单错误码与限流对照表.md, 星桥会议版本发布说明 v2.8.md

参考：网关按租户维度限流，阈值为每分钟 6000 次，超出返回 429 GATEWAY_RATE_LIMITED，并给出 X-XQ-Rate-Limit-Reset 响应头。

实际：未调用生成

引用：无

人工结论：待复核

### PD-23 我们忘了续费，多久之内补上钱数据不会被清理？

难度：numeric ｜ 库：product ｜ split：test

标注来源：星桥科技统一计费与续费口径说明.md

检索来源：星桥科技统一计费与续费口径说明.md, 星桥云盘套餐与配额对照表.md, 星桥会议录制与存储保留策略.md, 星桥云盘套餐与配额对照表.md, 星桥科技统一计费与续费口径说明.md

参考：续费到期后有 15 天宽限期，服务只读；宽限期后进入 90 天冻结期，冻结结束才进入数据清理流程，从到期到彻底清理约 105 天。

实际：未调用生成

引用：无

人工结论：待复核

### PD-24 会议室网络需要放通哪些 UDP 端口？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥会议音视频质量排查指南.md

检索来源：星桥会议版本发布说明 v2.8.md, 星桥会议音视频质量排查指南.md, 星桥会议常见问题 FAQ.md, 星桥会议产品功能手册.md, 星桥会议产品功能手册.md

参考：媒体流使用 UDP 50000 至 50100，信令走 TCP 443；会议室连接器还需要放通 TCP 8443。

实际：未调用生成

引用：无

人工结论：待复核

### PD-25 一线支持多久没给出方向就要把工单升级到二线？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥工单提交与升级机制.md

检索来源：星桥工单提交与升级机制.md, 星桥工单提交与升级机制.md, 星桥工单提交与升级机制.md, 星桥工单常见问题 FAQ.md, 星桥工单提交与升级机制.md

参考：一线在受理后 10 分钟内完成首次分类，30 分钟内无法给出明确方向应升级二线；二线 2 小时未定位根因且属 P0/P1 时升级三线。

实际：未调用生成

引用：无

人工结论：待复核

### PD-26 云盘的 Webhook 投递失败会重试几次，间隔怎么排？

难度：numeric ｜ 库：product ｜ split：test

标注来源：星桥云盘 Webhook 事件回调说明.md

检索来源：星桥工单通知模板与回调配置.md, 星桥云盘 Webhook 事件回调说明.md, 星桥云盘 Webhook 事件回调说明.md, 星桥云盘同步失败排查手册.md, 星桥科技 API 通用错误码与重试规范.md

参考：投递失败共重试 5 次，间隔为 10 秒、30 秒、90 秒、270 秒、810 秒，总跨度约 20 分钟；全部失败后可在 7 天内手工重放。

实际：未调用生成

引用：无

人工结论：待复核

### PD-27 调用云盘开放接口时，连接超时和读超时建议设多少秒？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥云盘开放接口接入指南.md

检索来源：星桥工单 SLA 分级与响应时限.md, 星桥云盘数据导入导出操作指南.md, 星桥工单接口鉴权与调用规范.md, 星桥科技 API 通用错误码与重试规范.md, 星桥云盘错误码说明.md

参考：连接超时建议 5 秒，读超时 30 秒（分片上传可放宽到 60 秒），重试 3 次，退避 1 秒、2 秒、4 秒。

实际：未调用生成

引用：无

人工结论：待复核

### PD-28 会议客户端多久没有心跳就会被判定掉线？

难度：numeric ｜ 库：product ｜ split：test

标注来源：星桥会议音视频质量排查指南.md

检索来源：星桥会议产品功能手册.md, 星桥会议音视频质量排查指南.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议错误码速查表.md, 星桥会议接口接入与鉴权指南.md

参考：心跳间隔为 5 秒，连续 3 次无响应即 15 秒判定掉线。

实际：未调用生成

引用：无

人工结论：待复核

### PD-29 我们想把云盘从 2.9 升到 3.x，起点版本要求和老客户端兼容情况怎么样？

难度：multi_source ｜ 库：product ｜ split：dev

标注来源：星桥云盘 3.x 升级说明.md, 星桥云盘客户端兼容性矩阵.md

检索来源：星桥云盘客户端兼容性矩阵.md, 星桥云盘 3.x 升级说明.md, 星桥云盘 2.x 升级说明.md, 星桥会议 1.x 客户端停用公告.md, 星桥云盘客户端兼容性矩阵.md

参考：3.x 升级要求先升到 2.9.7，服务端内存至少 16 GB、停机 90 分钟且不可回滚；客户端方面，2.9 及以下在 3.0 至 3.2 为只读，3.3.x 起拒绝登录，必须使用 3.0 及以上客户端。

实际：未调用生成

引用：无

人工结论：待复核

### PD-30 会议发起失败报了 429，处理方式和普通限流一样吗？

难度：multi_source ｜ 库：product ｜ split：dev

标注来源：星桥会议错误码速查表.md, 星桥科技 API 通用错误码与重试规范.md

检索来源：星桥会议错误码速查表.md, 星桥工单错误码与限流对照表.md, 星桥会议常见问题 FAQ.md, 星桥云盘错误码说明.md, 星桥云盘错误码说明.md

参考：会议 429 有两种：RATE_LIMITED 是每令牌每分钟 300 次调用频率超限，可退避重试；ROOM_LICENSE_EXHAUSTED 是并发会议室许可已满，需结束闲置会议或扩容。而 GATEWAY_RATE_LIMITED 属于统一网关的租户总量限流，三者不可套用同一处理方式。

实际：未调用生成

引用：无

人工结论：待复核

### PD-31 批量上传脚本偶发失败，是不是和并发数设置有关？

难度：multi_source ｜ 库：product ｜ split：test

标注来源：星桥云盘错误码说明.md, 星桥云盘同步失败排查手册.md

检索来源：星桥云盘数据导入导出操作指南.md, 星桥云盘错误码说明.md, 星桥工单常见故障排查.md, 星桥云盘数据导入导出操作指南.md, 星桥云盘错误码说明.md

参考：并发上传数超过 8 个会返回 429 UPLOAD_CONCURRENCY_EXCEEDED；处理办法是关闭部分上传任务，或把 drive.upload.parallel 调整为 4。

实际：未调用生成

引用：无

人工结论：待复核

### PD-32 工单通知收不到时，要同时检查哪两处配置？

难度：multi_source ｜ 库：product ｜ split：dev

标注来源：星桥工单通知模板与回调配置.md, 星桥工单常见故障排查.md

检索来源：星桥工单常见故障排查.md, 星桥工单常见故障排查.md, 星桥工单常见问题 FAQ.md, 星桥工单通知模板与回调配置.md, 星桥工单常见问题 FAQ.md

参考：一是邮件通道的 2525 端口是否放通（工单常见故障排查中给出该端口），二是 Webhook 回调的失败重试策略，回调失败重试 4 次。

实际：未调用生成

引用：无

人工结论：待复核

### PD-33 会议录制文件占用谁的存储配额，容量该怎么估？

难度：multi_source ｜ 库：product ｜ split：test

标注来源：星桥会议录制与存储保留策略.md, 星桥会议与云盘集成说明.md

检索来源：星桥会议录制与存储保留策略.md, 星桥会议与云盘集成说明.md, 星桥会议与云盘集成说明.md, 星桥会议套餐配额与并发说明.md, 星桥云盘产品功能手册.md

参考：录制文件计入云盘存储配额，存放在云盘存储配额对应的会议录制空间；1 小时 720p 录制约占 450 MB，1080p 约 900 MB。

实际：未调用生成

引用：无

人工结论：待复核

### PD-34 P0 工单首次响应到底按 15 分钟还是 30 分钟算？

难度：multi_source ｜ 库：product ｜ split：dev

标注来源：星桥工单 SLA 分级与响应时限.md, 星桥科技服务等级协议 SLA 总则.md

检索来源：星桥工单 SLA 分级与响应时限.md, 星桥科技服务等级协议 SLA 总则.md, 星桥科技服务等级协议 SLA 总则.md, 星桥工单提交与升级机制.md, 星桥科技服务等级协议 SLA 总则.md

参考：工单产品专章的 P0 首次响应为 15 分钟；公司总则的 30 分钟是兜底条款，两者存在差异时以产品专章为准，对客户按 15 分钟承诺。

实际：未调用生成

引用：无

人工结论：待复核

### PD-35 星桥云盘移动端有没有图片文字识别功能，能直接提取发票文字吗？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议与云盘集成说明.md, 星桥云盘产品功能手册.md, 星桥云盘产品功能手册.md, 星桥会议版本发布说明 v2.8.md, 星桥科技统一计费与续费口径说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-36 星桥工单能不能直接对接外部客户关系管理系统的原生连接器？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单与云盘集成配置说明.md, 星桥工单提交与升级机制.md, 星桥云盘产品功能手册.md, 星桥工单常见问题 FAQ.md, 星桥工单产品功能手册.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-37 星桥会议的端到端加密具体是怎么实现的，密钥由谁托管？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议与云盘集成说明.md, 星桥会议产品功能手册.md, 星桥会议录制与存储保留策略.md, 星桥会议常见问题 FAQ.md, 星桥会议预约与日历集成说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-38 星桥科技的安全审计报告是哪家机构出的，报告编号是多少？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥科技 API 通用错误码与重试规范.md, 星桥会议错误码速查表.md, 星桥科技统一账号与单点登录说明.md, 星桥工单错误码与限流对照表.md, 星桥云盘错误码说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-39 星桥云盘私有化部署通过了哪些国产化操作系统的认证？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘客户端兼容性矩阵.md, 星桥云盘版本发布说明 v3.4.md, 星桥云盘产品功能手册.md, 星桥云盘账号与共享授权说明.md, 星桥云盘版本发布说明 v3.4.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-40 星桥工单每个坐席一年的具体报价是多少钱？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议套餐配额与并发说明.md, 星桥科技统一计费与续费口径说明.md, 星桥工单通知模板与回调配置.md, 星桥工单提交与升级机制.md, 星桥会议套餐配额与并发说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-41 星桥会议的语音转写一共支持多少种语言，有小语种模型吗？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议版本发布说明 v2.8.md, 星桥会议产品功能手册.md, 星桥会议版本发布说明 v2.8.md, 星桥会议套餐配额与并发说明.md, 星桥会议与云盘集成说明.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-42 星桥云盘移动端支持分屏拖拽整理文件夹吗？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘产品功能手册.md, 星桥会议与云盘集成说明.md, 星桥云盘产品功能手册.md, 星桥云盘版本发布说明 v3.4.md, 星桥云盘数据备份与保留策略.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-43 星桥科技的数据中心一共在哪些城市，具体地址是什么？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘产品功能手册.md, 星桥会议套餐配额与并发说明.md, 星桥云盘数据备份与保留策略.md, 星桥工单提交与升级机制.md, 星桥云盘版本发布说明 v3.4.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-44 星桥工单支持填报工时并导出工时表吗？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单提交与升级机制.md, 星桥工单 SLA 分级与响应时限.md, 星桥工单通知模板与回调配置.md, 星桥工单常见问题 FAQ.md, 星桥工单产品功能手册.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-45 星桥云盘的 Webhook 签名用的是哪种哈希算法，密钥长度是多少位？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘 Webhook 事件回调说明.md, 星桥云盘开放接口接入指南.md, 星桥科技统一账号与单点登录说明.md, 星桥云盘版本发布说明 v3.4.md, 星桥工单通知模板与回调配置.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-46 会议录制文件的视频码率具体是多少 kbps？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议录制与存储保留策略.md, 星桥会议产品功能手册.md, 星桥会议产品功能手册.md, 星桥会议与云盘集成说明.md, 星桥会议音视频质量排查指南.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-47 工单满意度调查问卷一共有几道题，题目内容是什么？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单产品功能手册.md, 星桥工单产品功能手册.md, 星桥工单产品功能手册.md, 星桥工单常见问题 FAQ.md, 星桥科技服务等级协议 SLA 总则.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-48 星桥云盘 3.4.2 修复的安全问题对应哪个漏洞编号？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘错误码说明.md, 星桥科技 API 通用错误码与重试规范.md, 星桥云盘版本发布说明 v3.4.md, 星桥云盘同步失败排查手册.md, 星桥工单错误码与限流对照表.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-49 一台星桥会议连接器最多能同时承载几路会议？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议套餐配额与并发说明.md, 星桥会议版本发布说明 v2.8.md, 星桥会议套餐配额与并发说明.md, 星桥会议产品功能手册.md, 星桥会议产品功能手册.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-50 星桥工单自动分派里，技能组加权轮询的权重计算公式是什么？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单自动分派规则说明.md, 星桥工单自动分派规则说明.md, 星桥工单自动分派规则说明.md, 星桥工单错误码与限流对照表.md, 星桥工单产品功能手册.md

参考：（无）

实际：未调用生成

引用：无

人工结论：待复核

### PD-51 星桥云盘的回收站保留多少天，过期后还能恢复吗？

难度：cross_kb ｜ 库：product ｜ split：dev

标注来源：（期望拒答）

检索来源：正版软件授权与 License 台账.md, 权限申请与最小权限矩阵.md, 终端设备领用与归还登记表.md, 共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md

参考：答案只存在于产品知识库：星桥云盘回收站保留期为 30 天，超过后进入清理队列无法自助恢复。该问题在 IT 知识库中没有对应资料，跨库提问应当拒答。

实际：未调用生成

引用：无

人工结论：待复核

### PD-52 星桥工单 P0 事件的首次响应时限是多少分钟？

难度：cross_kb ｜ 库：product ｜ split：dev

标注来源：（期望拒答）

检索来源：统一身份认证（SSO）接入规范.md, 信息安全事件分级与上报流程.md, 信息安全事件分级与上报流程.md, 权限申请与最小权限矩阵.md, VPN 客户端故障排查清单.md

参考：答案只存在于产品知识库：星桥工单 P0 首次响应为 15 分钟、恢复 4 小时。该问题在 IT 知识库中无对应资料，跨库提问应当拒答。

实际：未调用生成

引用：无

人工结论：待复核

### PD-53 星桥会议接口的访问令牌有效期是多久，支持刷新吗？

难度：cross_kb ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, 权限申请与最小权限矩阵.md, 无线网络接入与访客 Wi-Fi 管理办法.md, AD 域账号与权限管理规定.md, 正版软件授权与 License 台账.md

参考：答案只存在于产品知识库：星桥会议接口访问令牌有效期 24 小时且不支持刷新令牌。该问题在 IT 知识库中无对应资料，跨库提问应当拒答。

实际：未调用生成

引用：无

人工结论：待复核

### PD-54 星桥云盘基础版套餐的存储配额是多少 GB？

难度：cross_kb ｜ 库：product ｜ split：dev

标注来源：（期望拒答）

检索来源：职级体系与薪资带宽表.md, 信息安全与数据保密规范.md, 请假类型与假期额度对照表.md, 关于调整 2026 年度差旅住宿标准的通知.md, 合规红线与行为准则.md

参考：答案只存在于产品知识库：星桥云盘基础版存储配额为 100 GB，标准版 1 TB。该问题在人力资源知识库中无对应资料，跨库提问应当拒答。

实际：未调用生成

引用：无

人工结论：待复核

### PD-55 星桥工单里单个附件的大小上限是多少兆？

难度：cross_kb ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：采购与付款审批权限表.md, 费用报销审批权限表.md, 合规红线与行为准则.md, 信息安全与数据保密规范.md, 用章与合同审批权限表.md

参考：答案只存在于产品知识库：星桥工单单个附件不超过 50 MB，单工单累计不超过 200 MB。该问题在人力资源知识库中无对应资料，跨库提问应当拒答。

实际：未调用生成

引用：无

人工结论：待复核

### PD-56 星桥会议媒体流使用的 UDP 端口范围是多少？

难度：cross_kb ｜ 库：product ｜ split：dev

标注来源：（期望拒答）

检索来源：职级体系与薪资带宽表.md, 信息安全与数据保密规范.md, 合规红线与行为准则.md, 采购与付款审批权限表.md, 培训管理办法.md

参考：答案只存在于产品知识库：星桥会议媒体流使用 UDP 50000 至 50100，信令走 TCP 443。该问题在人力资源知识库中无对应资料，跨库提问应拒答。

实际：未调用生成

引用：无

人工结论：待复核
