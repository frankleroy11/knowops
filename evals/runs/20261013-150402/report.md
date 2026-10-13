# KnowOps 星桥科技合成数据集评估

**重要声明**：本数据集全部为合成内容（虚构企业「星桥科技」），不对应任何真实企业制度、产品或人员。指标只代表在该合成语料上的表现，**不能**作为真实企业准确率或生产性能依据。

- 运行标识：synthetic-v1
- 题数：168（120 有答案 / 48 期望拒答）
- 知识库：it=评估-synthetic-v1-IT 支持, hr=评估-synthetic-v1-人事制度, product=评估-synthetic-v1-产品与客服
- 切片级判定：top_k 结果中是否存在同时命中标注来源文件与标注 terms 的切片

## 自动指标

```json
{
  "questions": 168,
  "successful_requests": 168,
  "answerable_questions": 120,
  "refusal_questions": 48,
  "source_recall_at_k": 0.8627,
  "chunk_recall_at_1": 0.6471,
  "chunk_recall_at_k": 0.6471,
  "mrr_at_k": 0.4456,
  "ndcg_at_k": 0.4943,
  "refusal_accuracy": 0.9583,
  "answerable_response_rate": 0.85,
  "citation_source_match_rate": 0.3725,
  "keyword_pass_rate_heuristic_only": 0.3627,
  "timings_ms": {
    "retrieval": {
      "p50": 418.07,
      "p95": 737.73
    },
    "chat": {
      "p50": 1987.74,
      "p95": 4096.23
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
    "answerable_questions": 18,
    "refusal_questions": 0,
    "source_recall_at_k": null,
    "chunk_recall_at_1": null,
    "chunk_recall_at_k": null,
    "mrr_at_k": null,
    "ndcg_at_k": null,
    "refusal_accuracy": null,
    "answerable_response_rate": 0.2222,
    "citation_source_match_rate": null,
    "keyword_pass_rate_heuristic_only": null,
    "timings_ms": {
      "retrieval": {
        "p50": 457.52,
        "p95": 624.8
      },
      "chat": {
        "p50": 1680.78,
        "p95": 3003.2
      }
    }
  },
  "easy": {
    "questions": 24,
    "successful_requests": 24,
    "answerable_questions": 24,
    "refusal_questions": 0,
    "source_recall_at_k": 0.9583,
    "chunk_recall_at_1": 0.75,
    "chunk_recall_at_k": 0.75,
    "mrr_at_k": 0.5278,
    "ndcg_at_k": 0.5776,
    "refusal_accuracy": null,
    "answerable_response_rate": 0.9167,
    "citation_source_match_rate": 0.25,
    "keyword_pass_rate_heuristic_only": 0.3333,
    "timings_ms": {
      "retrieval": {
        "p50": 382.94,
        "p95": 819.79
      },
      "chat": {
        "p50": 1973.53,
        "p95": 3046.08
      }
    }
  },
  "multi_source": {
    "questions": 18,
    "successful_requests": 18,
    "answerable_questions": 18,
    "refusal_questions": 0,
    "source_recall_at_k": 0.6111,
    "chunk_recall_at_1": 0.1667,
    "chunk_recall_at_k": 0.1667,
    "mrr_at_k": 0.1222,
    "ndcg_at_k": 0.1326,
    "refusal_accuracy": null,
    "answerable_response_rate": 1.0,
    "citation_source_match_rate": 0.3333,
    "keyword_pass_rate_heuristic_only": 0.6111,
    "timings_ms": {
      "retrieval": {
        "p50": 482.36,
        "p95": 770.25
      },
      "chat": {
        "p50": 3109.02,
        "p95": 11165.79
      }
    }
  },
  "numeric": {
    "questions": 30,
    "successful_requests": 30,
    "answerable_questions": 30,
    "refusal_questions": 0,
    "source_recall_at_k": 0.9,
    "chunk_recall_at_1": 0.7333,
    "chunk_recall_at_k": 0.7333,
    "mrr_at_k": 0.5055,
    "ndcg_at_k": 0.561,
    "refusal_accuracy": null,
    "answerable_response_rate": 0.9667,
    "citation_source_match_rate": 0.4,
    "keyword_pass_rate_heuristic_only": 0.3,
    "timings_ms": {
      "retrieval": {
        "p50": 398.08,
        "p95": 623.55
      },
      "chat": {
        "p50": 1918.01,
        "p95": 3675.04
      }
    }
  },
  "paraphrase": {
    "questions": 30,
    "successful_requests": 30,
    "answerable_questions": 30,
    "refusal_questions": 0,
    "source_recall_at_k": 0.9,
    "chunk_recall_at_1": 0.7667,
    "chunk_recall_at_k": 0.7667,
    "mrr_at_k": 0.5139,
    "ndcg_at_k": 0.5779,
    "refusal_accuracy": null,
    "answerable_response_rate": 0.9667,
    "citation_source_match_rate": 0.4667,
    "keyword_pass_rate_heuristic_only": 0.3,
    "timings_ms": {
      "retrieval": {
        "p50": 404.86,
        "p95": 699.22
      },
      "chat": {
        "p50": 2343.95,
        "p95": 5112.53
      }
    }
  },
  "refusal": {
    "questions": 48,
    "successful_requests": 48,
    "answerable_questions": 0,
    "refusal_questions": 48,
    "source_recall_at_k": null,
    "chunk_recall_at_1": null,
    "chunk_recall_at_k": null,
    "mrr_at_k": null,
    "ndcg_at_k": null,
    "refusal_accuracy": 0.9583,
    "answerable_response_rate": null,
    "citation_source_match_rate": null,
    "keyword_pass_rate_heuristic_only": null,
    "timings_ms": {
      "retrieval": {
        "p50": 416.73,
        "p95": 793.31
      },
      "chat": {
        "p50": 1762.36,
        "p95": 3027.57
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
    "answerable_questions": 73,
    "refusal_questions": 0,
    "source_recall_at_k": 0.871,
    "chunk_recall_at_1": 0.6129,
    "chunk_recall_at_k": 0.6129,
    "mrr_at_k": 0.4435,
    "ndcg_at_k": 0.4868,
    "refusal_accuracy": null,
    "answerable_response_rate": 0.8493,
    "citation_source_match_rate": 0.371,
    "keyword_pass_rate_heuristic_only": 0.4194,
    "timings_ms": {
      "retrieval": {
        "p50": 403.63,
        "p95": 730.95
      },
      "chat": {
        "p50": 2012.46,
        "p95": 4318.69
      }
    }
  },
  "test": {
    "questions": 95,
    "successful_requests": 95,
    "answerable_questions": 47,
    "refusal_questions": 48,
    "source_recall_at_k": 0.85,
    "chunk_recall_at_1": 0.7,
    "chunk_recall_at_k": 0.7,
    "mrr_at_k": 0.4487,
    "ndcg_at_k": 0.5059,
    "refusal_accuracy": 0.9583,
    "answerable_response_rate": 0.8511,
    "citation_source_match_rate": 0.375,
    "keyword_pass_rate_heuristic_only": 0.275,
    "timings_ms": {
      "retrieval": {
        "p50": 431.98,
        "p95": 793.31
      },
      "chat": {
        "p50": 1974.09,
        "p95": 4096.23
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
    "answerable_questions": 40,
    "refusal_questions": 16,
    "source_recall_at_k": 0.9412,
    "chunk_recall_at_1": 0.6176,
    "chunk_recall_at_k": 0.6176,
    "mrr_at_k": 0.3515,
    "ndcg_at_k": 0.4192,
    "refusal_accuracy": 0.9375,
    "answerable_response_rate": 0.825,
    "citation_source_match_rate": 0.3824,
    "keyword_pass_rate_heuristic_only": 0.1471,
    "timings_ms": {
      "retrieval": {
        "p50": 383.76,
        "p95": 538.85
      },
      "chat": {
        "p50": 2019.8,
        "p95": 5112.53
      }
    }
  },
  "it": {
    "questions": 56,
    "successful_requests": 56,
    "answerable_questions": 40,
    "refusal_questions": 16,
    "source_recall_at_k": 0.8235,
    "chunk_recall_at_1": 0.7059,
    "chunk_recall_at_k": 0.7059,
    "mrr_at_k": 0.5833,
    "ndcg_at_k": 0.6116,
    "refusal_accuracy": 1.0,
    "answerable_response_rate": 0.875,
    "citation_source_match_rate": 0.4706,
    "keyword_pass_rate_heuristic_only": 0.4412,
    "timings_ms": {
      "retrieval": {
        "p50": 423.8,
        "p95": 793.31
      },
      "chat": {
        "p50": 1903.84,
        "p95": 3003.2
      }
    }
  },
  "product": {
    "questions": 56,
    "successful_requests": 56,
    "answerable_questions": 40,
    "refusal_questions": 16,
    "source_recall_at_k": 0.8235,
    "chunk_recall_at_1": 0.6176,
    "chunk_recall_at_k": 0.6176,
    "mrr_at_k": 0.402,
    "ndcg_at_k": 0.4519,
    "refusal_accuracy": 0.9375,
    "answerable_response_rate": 0.85,
    "citation_source_match_rate": 0.2647,
    "keyword_pass_rate_heuristic_only": 0.5,
    "timings_ms": {
      "retrieval": {
        "p50": 483.23,
        "p95": 755.52
      },
      "chat": {
        "p50": 2252.37,
        "p95": 4318.69
      }
    }
  }
}
```

## 逐题结果

|题号|库|难度|类型|文档命中|切片命中|MRR|引用匹配|正确拒答|
|---|---|---|---|---|---|---|---|---|
|HR-01|hr|easy|answerable|True|True|0.3333|False|-|
|HR-02|hr|easy|answerable|True|True|0.5|True|-|
|HR-03|hr|easy|answerable|True|True|0.3333|False|-|
|HR-04|hr|easy|answerable|True|True|0.3333|False|-|
|HR-05|hr|easy|answerable|True|True|0.5|True|-|
|HR-06|hr|easy|answerable|True|True|1.0|False|-|
|HR-07|hr|easy|answerable|True|False|0.0|False|-|
|HR-08|hr|easy|answerable|True|True|0.5|False|-|
|HR-09|hr|paraphrase|answerable|True|False|0.0|False|-|
|HR-10|hr|paraphrase|answerable|True|True|0.25|False|-|
|HR-11|hr|paraphrase|answerable|True|False|0.0|False|-|
|HR-12|hr|paraphrase|answerable|True|True|0.5|False|-|
|HR-13|hr|paraphrase|answerable|True|True|0.5|True|-|
|HR-14|hr|paraphrase|answerable|True|False|0.0|True|-|
|HR-15|hr|paraphrase|answerable|True|True|0.5|True|-|
|HR-16|hr|paraphrase|answerable|True|True|1.0|True|-|
|HR-17|hr|paraphrase|answerable|True|True|0.3333|True|-|
|HR-18|hr|paraphrase|answerable|True|True|1.0|False|-|
|HR-19|hr|numeric|answerable|True|False|0.0|False|-|
|HR-20|hr|numeric|answerable|True|False|0.0|False|-|
|HR-21|hr|numeric|answerable|True|False|0.0|False|-|
|HR-22|hr|numeric|answerable|True|False|0.0|False|-|
|HR-23|hr|numeric|answerable|True|True|1.0|True|-|
|HR-24|hr|numeric|answerable|True|True|1.0|False|-|
|HR-25|hr|numeric|answerable|True|True|1.0|False|-|
|HR-26|hr|numeric|answerable|True|True|0.5|True|-|
|HR-27|hr|numeric|answerable|True|True|0.3333|True|-|
|HR-28|hr|numeric|answerable|True|True|0.3333|True|-|
|HR-29|hr|multi_source|answerable|True|False|0.0|False|-|
|HR-30|hr|multi_source|answerable|True|False|0.0|False|-|
|HR-31|hr|multi_source|answerable|False|False|0.0|False|-|
|HR-32|hr|multi_source|answerable|True|True|0.2|True|-|
|HR-33|hr|multi_source|answerable|True|False|0.0|True|-|
|HR-34|hr|multi_source|answerable|False|False|0.0|False|-|
|HR-35|hr|refusal|refusal|None|None|None|-|True|
|HR-36|hr|refusal|refusal|None|None|None|-|True|
|HR-37|hr|refusal|refusal|None|None|None|-|True|
|HR-38|hr|refusal|refusal|None|None|None|-|True|
|HR-39|hr|refusal|refusal|None|None|None|-|True|
|HR-40|hr|refusal|refusal|None|None|None|-|True|
|HR-41|hr|refusal|refusal|None|None|None|-|True|
|HR-42|hr|refusal|refusal|None|None|None|-|True|
|HR-43|hr|refusal|refusal|None|None|None|-|True|
|HR-44|hr|refusal|refusal|None|None|None|-|True|
|HR-45|hr|refusal|refusal|None|None|None|-|True|
|HR-46|hr|refusal|refusal|None|None|None|-|True|
|HR-47|hr|refusal|refusal|None|None|None|-|False|
|HR-48|hr|refusal|refusal|None|None|None|-|True|
|HR-49|hr|refusal|refusal|None|None|None|-|True|
|HR-50|hr|refusal|refusal|None|None|None|-|True|
|HR-51|hr|cross_kb|answerable|None|None|None|-|True|
|HR-52|hr|cross_kb|answerable|None|None|None|-|True|
|HR-53|hr|cross_kb|answerable|None|None|None|-|True|
|HR-54|hr|cross_kb|answerable|None|None|None|-|True|
|HR-55|hr|cross_kb|answerable|None|None|None|-|True|
|HR-56|hr|cross_kb|answerable|None|None|None|-|True|
|IT-01|it|easy|answerable|False|False|0.0|False|-|
|IT-02|it|easy|answerable|True|False|0.0|False|-|
|IT-03|it|easy|answerable|True|True|1.0|False|-|
|IT-04|it|easy|answerable|True|True|1.0|True|-|
|IT-05|it|easy|answerable|True|True|1.0|True|-|
|IT-06|it|easy|answerable|True|True|1.0|False|-|
|IT-07|it|easy|answerable|True|True|1.0|True|-|
|IT-08|it|easy|answerable|True|True|0.3333|True|-|
|IT-09|it|paraphrase|answerable|True|False|0.0|True|-|
|IT-10|it|paraphrase|answerable|True|True|1.0|False|-|
|IT-11|it|paraphrase|answerable|True|True|1.0|False|-|
|IT-12|it|paraphrase|answerable|True|True|0.3333|False|-|
|IT-13|it|paraphrase|answerable|True|True|1.0|True|-|
|IT-14|it|paraphrase|answerable|True|True|1.0|False|-|
|IT-15|it|paraphrase|answerable|True|True|1.0|True|-|
|IT-16|it|paraphrase|answerable|True|True|1.0|True|-|
|IT-17|it|paraphrase|answerable|True|True|1.0|False|-|
|IT-18|it|paraphrase|answerable|True|True|0.3333|True|-|
|IT-19|it|numeric|answerable|True|True|1.0|False|-|
|IT-20|it|numeric|answerable|False|False|0.0|False|-|
|IT-21|it|numeric|answerable|False|False|0.0|False|-|
|IT-22|it|numeric|answerable|True|True|1.0|True|-|
|IT-23|it|numeric|answerable|True|True|1.0|False|-|
|IT-24|it|numeric|answerable|True|True|0.5|False|-|
|IT-25|it|numeric|answerable|True|True|1.0|True|-|
|IT-26|it|numeric|answerable|True|True|0.5|True|-|
|IT-27|it|numeric|answerable|True|True|0.3333|True|-|
|IT-28|it|numeric|answerable|True|True|0.5|True|-|
|IT-29|it|multi_source|answerable|False|True|1.0|False|-|
|IT-30|it|multi_source|answerable|True|False|0.0|False|-|
|IT-31|it|multi_source|answerable|False|False|0.0|False|-|
|IT-32|it|multi_source|answerable|True|False|0.0|True|-|
|IT-33|it|multi_source|answerable|True|False|0.0|True|-|
|IT-34|it|multi_source|answerable|False|False|0.0|False|-|
|IT-35|it|refusal|refusal|None|None|None|-|True|
|IT-36|it|refusal|refusal|None|None|None|-|True|
|IT-37|it|refusal|refusal|None|None|None|-|True|
|IT-38|it|refusal|refusal|None|None|None|-|True|
|IT-39|it|refusal|refusal|None|None|None|-|True|
|IT-40|it|refusal|refusal|None|None|None|-|True|
|IT-41|it|refusal|refusal|None|None|None|-|True|
|IT-42|it|refusal|refusal|None|None|None|-|True|
|IT-43|it|refusal|refusal|None|None|None|-|True|
|IT-44|it|refusal|refusal|None|None|None|-|True|
|IT-45|it|refusal|refusal|None|None|None|-|True|
|IT-46|it|refusal|refusal|None|None|None|-|True|
|IT-47|it|refusal|refusal|None|None|None|-|True|
|IT-48|it|refusal|refusal|None|None|None|-|True|
|IT-49|it|refusal|refusal|None|None|None|-|True|
|IT-50|it|refusal|refusal|None|None|None|-|True|
|IT-51|it|cross_kb|answerable|None|None|None|-|False|
|IT-52|it|cross_kb|answerable|None|None|None|-|False|
|IT-53|it|cross_kb|answerable|None|None|None|-|True|
|IT-54|it|cross_kb|answerable|None|None|None|-|True|
|IT-55|it|cross_kb|answerable|None|None|None|-|True|
|IT-56|it|cross_kb|answerable|None|None|None|-|False|
|PD-01|product|easy|answerable|True|False|0.0|False|-|
|PD-02|product|easy|answerable|True|False|0.0|False|-|
|PD-03|product|easy|answerable|True|True|1.0|False|-|
|PD-04|product|easy|answerable|True|False|0.0|False|-|
|PD-05|product|easy|answerable|True|True|0.5|False|-|
|PD-06|product|easy|answerable|True|True|1.0|False|-|
|PD-07|product|easy|answerable|True|True|0.3333|False|-|
|PD-08|product|easy|answerable|True|True|1.0|False|-|
|PD-09|product|paraphrase|answerable|True|True|0.3333|False|-|
|PD-10|product|paraphrase|answerable|True|True|0.25|False|-|
|PD-11|product|paraphrase|answerable|False|False|0.0|False|-|
|PD-12|product|paraphrase|answerable|False|False|0.0|False|-|
|PD-13|product|paraphrase|answerable|True|True|0.3333|True|-|
|PD-14|product|paraphrase|answerable|False|False|0.0|False|-|
|PD-15|product|paraphrase|answerable|True|True|1.0|False|-|
|PD-16|product|paraphrase|answerable|True|True|0.5|True|-|
|PD-17|product|paraphrase|answerable|True|True|1.0|True|-|
|PD-18|product|paraphrase|answerable|True|True|0.25|True|-|
|PD-19|product|numeric|answerable|True|True|1.0|True|-|
|PD-20|product|numeric|answerable|True|True|0.3333|False|-|
|PD-21|product|numeric|answerable|True|True|0.3333|True|-|
|PD-22|product|numeric|answerable|True|True|1.0|False|-|
|PD-23|product|numeric|answerable|True|True|1.0|False|-|
|PD-24|product|numeric|answerable|True|True|0.5|False|-|
|PD-25|product|numeric|answerable|True|True|0.5|True|-|
|PD-26|product|numeric|answerable|True|True|0.5|False|-|
|PD-27|product|numeric|answerable|False|False|0.0|False|-|
|PD-28|product|numeric|answerable|True|False|0.0|False|-|
|PD-29|product|multi_source|answerable|True|False|0.0|True|-|
|PD-30|product|multi_source|answerable|False|False|0.0|False|-|
|PD-31|product|multi_source|answerable|False|False|0.0|False|-|
|PD-32|product|multi_source|answerable|True|False|0.0|False|-|
|PD-33|product|multi_source|answerable|True|True|1.0|False|-|
|PD-34|product|multi_source|answerable|True|False|0.0|True|-|
|PD-35|product|refusal|refusal|None|None|None|-|True|
|PD-36|product|refusal|refusal|None|None|None|-|True|
|PD-37|product|refusal|refusal|None|None|None|-|True|
|PD-38|product|refusal|refusal|None|None|None|-|True|
|PD-39|product|refusal|refusal|None|None|None|-|True|
|PD-40|product|refusal|refusal|None|None|None|-|True|
|PD-41|product|refusal|refusal|None|None|None|-|True|
|PD-42|product|refusal|refusal|None|None|None|-|True|
|PD-43|product|refusal|refusal|None|None|None|-|True|
|PD-44|product|refusal|refusal|None|None|None|-|True|
|PD-45|product|refusal|refusal|None|None|None|-|True|
|PD-46|product|refusal|refusal|None|None|None|-|True|
|PD-47|product|refusal|refusal|None|None|None|-|True|
|PD-48|product|refusal|refusal|None|None|None|-|True|
|PD-49|product|refusal|refusal|None|None|None|-|False|
|PD-50|product|refusal|refusal|None|None|None|-|True|
|PD-51|product|cross_kb|answerable|None|None|None|-|False|
|PD-52|product|cross_kb|answerable|None|None|None|-|True|
|PD-53|product|cross_kb|answerable|None|None|None|-|True|
|PD-54|product|cross_kb|answerable|None|None|None|-|True|
|PD-55|product|cross_kb|answerable|None|None|None|-|True|
|PD-56|product|cross_kb|answerable|None|None|None|-|True|

## 人工复核

逐题核对答案正确性与原文支持程度；未复核题目的人工分数留空。

### HR-01 每个月几号发工资？遇到周末会提前吗？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：薪酬结构与发薪日历说明.md

检索来源：薪酬结构与发薪日历说明.md, 薪酬结构与发薪日历说明.md, 薪酬结构与发薪日历说明.md, 值班与加班补贴说明.md, 员工关系与假期常见问题 FAQ.md

参考：每月 15 日发放上一个自然月的工资；遇法定节假日或双休日提前至最近一个工作日。

实际：每个月15号发工资，遇到周末或节假日会提前到最近一个工作日。

引用：薪酬结构与发薪日历说明.md, 薪酬结构与发薪日历说明.md, 员工关系与假期常见问题 FAQ.md

人工结论：待复核

### HR-02 公积金公司和个人各交多少？

难度：easy ｜ 库：hr ｜ split：test

标注来源：社会保险与住房公积金管理办法.md

检索来源：社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 报销与出差常见问题 FAQ.md, 补充医疗保险与年度体检福利说明.md

参考：公司与个人缴存比例均为 12%，缴存基数与社保基数一致。

实际：公积金公司和个人各交12%，缴存基数与社保基数一致。

引用：社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md

人工结论：待复核

### HR-03 婚假有几天？什么时候必须休完？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：请假与休假管理制度.md

检索来源：请假与休假管理制度.md, 员工关系与假期常见问题 FAQ.md, 请假与休假管理制度.md, 请假类型与假期额度对照表.md, 请假类型与假期额度对照表.md

参考：婚假 10 个自然日，须在领取结婚证之日起 12 个月内休完。

实际：婚假为10个自然日，须在领取结婚证之日起12个月内休完。

引用：员工关系与假期常见问题 FAQ.md, 请假与休假管理制度.md, 请假类型与假期额度对照表.md

人工结论：待复核

### HR-04 公司年度体检的标准是多少钱？

难度：easy ｜ 库：hr ｜ split：test

标注来源：补充医疗保险与年度体检福利说明.md

检索来源：补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md, 报销与出差常见问题 FAQ.md

参考：1200 元/人；40 周岁及以上员工为 2000 元/人。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-05 春节公司发什么福利？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：节日福利与团建经费管理办法.md

检索来源：节日福利与团建经费管理办法.md, 节日福利与团建经费管理办法.md, 节日福利与团建经费管理办法.md, 报销与出差常见问题 FAQ.md, 年终奖与绩效奖金发放办法.md

参考：800 元/人的实物礼包加平台积分。

实际：春节公司发放800元/人的福利，形式为实物礼包加平台积分。

引用：节日福利与团建经费管理办法.md, 节日福利与团建经费管理办法.md

人工结论：待复核

### HR-06 辞职要提前多久通知公司？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：离职管理与工作交接流程.md

检索来源：离职管理与工作交接流程.md, 员工关系与假期常见问题 FAQ.md, 离职管理与工作交接流程.md, 离职证明与竞业限制说明.md, 离职管理与工作交接流程.md

参考：正式员工须提前 30 日书面通知；试用期员工提前 3 日。

实际：正式员工主动辞职须提前30日以书面形式通知公司；试用期员工主动辞职须提前3日书面通知公司。

引用：离职管理与工作交接流程.md, 员工关系与假期常见问题 FAQ.md, 离职管理与工作交接流程.md

人工结论：待复核

### HR-07 公司账号密码多久要换一次？

难度：easy ｜ 库：hr ｜ split：test

标注来源：信息安全与数据保密规范.md

检索来源：信息安全与数据保密规范.md, 关于启用新版考勤与请假制度的通知.md, 员工关系与假期常见问题 FAQ.md, hr-leave-quota-card.pdf, hr-travel-reimbursement-card.pdf

参考：每 90 天更换一次，且不得与前 5 次使用过的密码重复。

实际：公司账号密码每90天更换一次，不得与前5次重复。

引用：信息安全与数据保密规范.md, 员工关系与假期常见问题 FAQ.md

人工结论：待复核

### HR-08 签 3 年期限的劳动合同，试用期是多久？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：员工入职办理指南.md

检索来源：新员工试用期管理与转正流程.md, 员工入职办理指南.md, 病假管理与医疗期说明.md, 员工关系与假期常见问题 FAQ.md, 员工关系与假期常见问题 FAQ.md

参考：试用期为 3 个月，试用期工资按定薪的 90% 发放。

实际：签3年期限的劳动合同，试用期为3个月。

引用：新员工试用期管理与转正流程.md, 员工入职办理指南.md, 员工关系与假期常见问题 FAQ.md

人工结论：待复核

### HR-09 我早上晚打卡了十几分钟，会被扣多少钱？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：考勤管理与打卡规范.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 日常费用报销管理办法.md, 关于启用新版考勤与请假制度的通知.md

参考：迟到 30 分钟以内每次扣发当月工资 50 元；超过 30 分钟按事假半天计。

实际：早上晚打卡十几分钟属于迟到，若在30分钟内，扣50元；但需确认是否适用弹性工作制（如适用，则上班打卡截止时间为10:30，不扣款）。资料未说明您的具体岗位或所在地，无法判断是否适用弹性工作制。

引用：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 关于启用新版考勤与请假制度的通知.md

人工结论：待复核

### HR-10 忘记打卡的话，一个月最多能补几次？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：考勤管理与打卡规范.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 关于启用新版考勤与请假制度的通知.md, 考勤管理与打卡规范.md, 关于启用新版考勤与请假制度的通知.md

参考：每月最多补卡 3 次，须在事发后 24 小时内提交。

实际：一个月最多能补3次卡。

引用：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 关于启用新版考勤与请假制度的通知.md

人工结论：待复核

### HR-11 以前那份差旅住宿标准是不是作废了？现在按哪个文件执行？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：关于调整 2026 年度差旅住宿标准的通知.md

检索来源：关于调整 2026 年度差旅住宿标准的通知.md, 关于调整 2026 年度差旅住宿标准的通知.md, 差旅报销标准（其他城市）.md, 已废止制度清单与替代关系说明.md, 已废止制度清单与替代关系说明.md

参考：《差旅报销标准（2024 版）》自 2026 年 1 月 1 日起废止，现行以《差旅报销标准（一线城市）》与《差旅报销标准（其他城市）》为准。

实际：是的，以前的差旅住宿标准已作废。《差旅报销标准（2024 版）》（XQ-FIN-010-V3）和《差旅报销标准（2024 版·其他城市）》（XQ-FIN-011-V2）均自2026年1月1日起废止。当前执行的是：一线城市适用《差旅报销标准（一线城市）》（XQ-FIN-010），住宿费上限为600元/晚；其他城市适用《差旅报销标准（其他城市）》（XQ-FIN-011），住宿费上限为450元/晚。

引用：关于调整 2026 年度差旅住宿标准的通知.md, 关于调整 2026 年度差旅住宿标准的通知.md, 差旅报销标准（其他城市）.md, 已废止制度清单与替代关系说明.md

人工结论：待复核

### HR-12 我们部门团建一年人均能花多少钱？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：餐饮与团建费用报销口径.md

检索来源：餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md, 节日福利与团建经费管理办法.md

参考：每人每季度 200 元，全年每人累计不超过 800 元。

实际：我们部门团建一年人均能花800元。根据规定，团建经费按部门在编人数核定，每人每季度200元，全年累计不超过800元。

引用：餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md, 节日福利与团建经费管理办法.md

人工结论：待复核

### HR-13 我每年买办公用品的预算是多少？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：办公用品采购与报销标准.md

检索来源：办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 报销与出差常见问题 FAQ.md

参考：1200 元/人，超出部分须部门负责人审批。

实际：你每年买办公用品的预算是1200元/人。

引用：办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 办公用品采购与报销标准.md

人工结论：待复核

### HR-14 周末值班能不能像加班那样换成调休？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：值班与加班补贴说明.md

检索来源：值班与加班补贴说明.md, 值班与加班补贴说明.md, 加班与调休管理办法.md, 加班与调休管理办法.md, 值班与加班补贴说明.md

参考：不能。值班只发补贴，休息日值班 300 元/次，不折算调休；只有被认定为加班的部分才能按倍数折算调休。

实际：不能。周末（休息日）值班以300元/次的值班补贴方式补偿，不折算调休。只有被明确认定为加班的部分（如连续实质性工作超过4小时），才可按2倍标准折算调休；值班与加班按“择一适用”原则处理，不得重复享受。

引用：值班与加班补贴说明.md, 值班与加班补贴说明.md, 值班与加班补贴说明.md

人工结论：待复核

### HR-15 绩效评级里拿 S 的人大概占多少比例？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：绩效考核管理办法.md

检索来源：绩效考核管理办法.md, 绩效考核管理办法.md, 绩效评级与结果应用说明.md, 绩效考核管理办法.md, 绩效评级与结果应用说明.md

参考：S 级 10%，A 级 25%，B 级 50%，C 级 12%，D 级 3%。

实际：绩效评级里拿 S 的人大概占 10%。

引用：绩效考核管理办法.md, 绩效考核管理办法.md, 绩效考核管理办法.md

人工结论：待复核

### HR-16 连续两个季度评 D 会有什么后果？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：绩效评级与结果应用说明.md

检索来源：绩效评级与结果应用说明.md, 绩效评级与结果应用说明.md, 绩效考核管理办法.md, 绩效考核管理办法.md, 绩效考核管理办法.md

参考：进入为期 3 个月的绩效改进计划（PIP）。

实际：连续两个季度评 D 的员工将进入为期 3 个月的绩效改进计划（PIP）；PIP 期间由直属主管制定改进目标并每周回顾进展；PIP 期满评估未达标的，公司可依法调整岗位或解除劳动合同。

引用：绩效评级与结果应用说明.md, 绩效评级与结果应用说明.md

人工结论：待复核

### HR-17 竞业限制一般要持续多久？补偿怎么算？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：离职证明与竞业限制说明.md

检索来源：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 日常费用报销管理办法.md, 绩效考核管理办法.md

参考：期限最长不超过 12 个月；补偿为离职前 12 个月平均工资的 30%，按月发放。

实际：竞业限制期限最长不超过12个月，自离职之日起算；补偿标准为员工离职前12个月平均工资的30%，按月发放。

引用：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md

人工结论：待复核

### HR-18 提交申诉后多久能拿到结果？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：员工申诉与投诉处理流程.md

检索来源：员工申诉与投诉处理流程.md, 员工申诉与投诉处理流程.md, 绩效考核管理办法.md, 员工关系与假期常见问题 FAQ.md, 员工申诉与投诉处理流程.md

参考：受理时限 3 个工作日，自受理之日起 15 个工作日内给出书面结论。

实际：自受理之日起15个工作日内给出书面结论；需要延长的须书面告知，延长不超过10个工作日。

引用：员工申诉与投诉处理流程.md, 员工申诉与投诉处理流程.md, 员工关系与假期常见问题 FAQ.md

人工结论：待复核

### HR-19 去上海出差，住宿一晚最多能报销多少钱？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：差旅报销标准（一线城市）.md

检索来源：差旅报销标准（一线城市）.md, 报销与出差常见问题 FAQ.md, 差旅报销标准（一线城市）.md, 差旅报销标准（一线城市）.md, 差旅报销标准（其他城市）.md

参考：600 元/晚，据实报销，超出部分由员工自理。

实际：去上海出差，住宿一晚最多能报销600元。

引用：差旅报销标准（一线城市）.md, 报销与出差常见问题 FAQ.md, 差旅报销标准（一线城市）.md, 差旅报销标准（一线城市）.md

人工结论：待复核

### HR-20 去成都出差，住宿每晚的上限是多少？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：差旅报销标准（其他城市）.md

检索来源：关于调整 2026 年度差旅住宿标准的通知.md, 差旅报销标准（其他城市）.md, 差旅报销标准（一线城市）.md, 关于调整 2026 年度差旅住宿标准的通知.md, 报销与出差常见问题 FAQ.md

参考：450 元/晚。

实际：去成都出差，住宿每晚的上限是450元。成都不属于北京、上海、广州、深圳四个一线城市，因此适用“其他城市”标准。

引用：差旅报销标准（其他城市）.md, 关于调整 2026 年度差旅住宿标准的通知.md, 报销与出差常见问题 FAQ.md

人工结论：待复核

### HR-21 我在公司干了 6 年，年假能有几天？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：请假类型与假期额度对照表.md

检索来源：员工关系与假期常见问题 FAQ.md, 请假与休假管理制度.md, 请假类型与假期额度对照表.md, 请假类型与假期额度对照表.md, 病假管理与医疗期说明.md

参考：15 天。

实际：根据公司制度，您在公司工作满6年（即司龄满5年不满10年），可享受15天带薪年休假。

引用：员工关系与假期常见问题 FAQ.md, 请假与休假管理制度.md, 请假类型与假期额度对照表.md

人工结论：待复核

### HR-22 病假超过 5 天以后，工资按几成发？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：请假类型与假期额度对照表.md

检索来源：病假管理与医疗期说明.md, 病假管理与医疗期说明.md, 病假管理与医疗期说明.md, 病假管理与医疗期说明.md, 请假类型与假期额度对照表.md

参考：超出 5 天的部分按本人日工资的 60% 计发。

实际：病假超过5天以后，工资按六成（60%）发放。

引用：病假管理与医疗期说明.md, 病假管理与医疗期说明.md, 请假类型与假期额度对照表.md

人工结论：待复核

### HR-23 加班换来的调休多久不用就会作废？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：加班与调休管理办法.md

检索来源：加班与调休管理办法.md, 加班与调休管理办法.md, 加班与调休管理办法.md, 加班与调休管理办法.md, 关于启用新版考勤与请假制度的通知.md

参考：自加班发生之日起 6 个月，逾期自动作废，不予折现。

实际：加班换来的调休自加班发生之日起6个月内未使用即自动作废，不予折现。

引用：加班与调休管理办法.md, 加班与调休管理办法.md

人工结论：待复核

### HR-24 一笔 4800 元的差旅报销要走谁的审批？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：费用报销审批权限表.md

检索来源：费用报销审批权限表.md, 费用报销审批权限表.md, 费用报销审批权限表.md, 报销与出差常见问题 FAQ.md, 费用报销审批权限表.md

参考：属 1000 元（含）至 5000 元档，由直属主管与部门负责人审批。

实际：一笔4800元的差旅报销属于1000元（含）至5000元档，由直属主管与部门负责人审批。

引用：费用报销审批权限表.md, 费用报销审批权限表.md, 费用报销审批权限表.md, 报销与出差常见问题 FAQ.md, 费用报销审批权限表.md

人工结论：待复核

### HR-25 我们部门要添置一套约 3 万元的测试设备，审批流程要走到哪一级？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：采购与付款审批权限表.md

检索来源：采购与付款审批权限表.md, 报销与出差常见问题 FAQ.md, 采购与付款审批权限表.md, 办公用品采购与报销标准.md, 采购与付款审批权限表.md

参考：属 5000 元（含）至 50000 元档，由部门负责人、采购负责人与财务负责人审批。

实际：需要由部门负责人、采购负责人与财务负责人三级审批。

引用：采购与付款审批权限表.md, 报销与出差常见问题 FAQ.md, 采购与付款审批权限表.md

人工结论：待复核

### HR-26 2026 年社保缴费基数的上下限是多少？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：社会保险与住房公积金管理办法.md

检索来源：社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 已废止制度清单与替代关系说明.md, 关于调整 2026 年度差旅住宿标准的通知.md

参考：上限 35283 元/月，下限 6821 元/月。

实际：2026年社保缴费基数上限为35283元/月，下限为6821元/月。

引用：社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md

人工结论：待复核

### HR-27 P6 员工的年终奖基数是几个月工资？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：年终奖与绩效奖金发放办法.md

检索来源：年终奖与绩效奖金发放办法.md, 年终奖与绩效奖金发放办法.md, 年终奖与绩效奖金发放办法.md, 绩效评级与结果应用说明.md, 职级体系与薪资带宽表.md

参考：2 个月固定薪资。

实际：P6 员工的年终奖基数是2个月工资。

引用：年终奖与绩效奖金发放办法.md, 年终奖与绩效奖金发放办法.md

人工结论：待复核

### HR-28 转正评估一般是什么时候启动？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：新员工试用期管理与转正流程.md

检索来源：新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 绩效考核管理办法.md, 晋升与调岗管理办法.md

参考：试用期届满前 10 个工作日启动转正评估。

实际：转正评估一般在试用期届满前10个工作日启动。

引用：新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md

人工结论：待复核

### HR-29 去上海出差 3 天 2 晚，补贴和住宿分别按什么标准算？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：出差管理办法.md, 差旅报销标准（一线城市）.md

检索来源：差旅报销标准（一线城市）.md, 出差管理办法.md, 出差管理办法.md, 报销与出差常见问题 FAQ.md, 关于调整 2026 年度差旅住宿标准的通知.md

参考：出差补贴 150 元/天（出发与返回当日各按半天计）；住宿上限 600 元/晚据实报销。两份文件各提供一半口径。

实际：去上海出差3天2晚，住宿标准为600元/晚，据实报销，超出部分自理；出差补贴标准为150元/天，按3个自然日计算共450元。补贴已包含伙食与市内短途交通费用，不再另行报销。

引用：差旅报销标准（一线城市）.md, 出差管理办法.md, 出差管理办法.md, 报销与出差常见问题 FAQ.md

人工结论：待复核

### HR-30 年假没休完能折成钱吗？在职和离职有区别吗？

难度：multi_source ｜ 库：hr ｜ split：test

标注来源：请假与休假管理制度.md, 请假类型与假期额度对照表.md

检索来源：年终奖与绩效奖金发放办法.md, 请假与休假管理制度.md, 离职管理与工作交接流程.md, 离职管理与工作交接流程.md, 请假类型与假期额度对照表.md

参考：在职员工可在次年 3 月 31 日前申请折现，每年最多 5 天；离职时当年度应休未休年假按日工资 100% 折现，同样最多 5 天。

实际：年假未休完可以折现，但仅限离职时或次年3月31日前申请折现，每年最多折现5天，按日工资100%计算。在职期间原则上不可折现，但可在次年3月31日前申请折现（见来源2第十条）；离职时未休年假必须折现（见来源3第五条、来源5第2.3条）。因此，在职与离职有区别：在职员工需在规定时限内主动申请折现，而离职员工的未休年假自动纳入离职结算折现。

引用：请假与休假管理制度.md, 离职管理与工作交接流程.md, 请假类型与假期额度对照表.md

人工结论：待复核

### HR-31 加班到晚上十一点打车回家，这笔钱怎么报？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：加班与调休管理办法.md, 日常费用报销管理办法.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 差旅报销标准（其他城市）.md, 餐饮与团建费用报销口径.md, 报销与出差常见问题 FAQ.md

参考：加班至 22:00 之后可据实报销当日自公司至居住地的打车费，单次上限 120 元。

实际：加班到晚上十一点打车回家，可以报销，单次上限120元。需在费用发生后30个自然日内提交报销，并注明起讫地点与业务事由；若单次打车费超过200元，须经部门负责人审批。

引用：报销与出差常见问题 FAQ.md

人工结论：待复核

### HR-32 试用期员工的绩效考核和转正评估分别怎么安排？

难度：multi_source ｜ 库：hr ｜ split：test

标注来源：新员工试用期管理与转正流程.md, 绩效考核管理办法.md

检索来源：新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 绩效考核管理办法.md, 绩效考核管理办法.md

参考：入职不满 2 个月不参与当季季度考核；转正评估单独使用《转正评估表》，在试用期届满前 10 个工作日启动。

实际：试用期员工的绩效考核与转正评估是两个独立但关联的安排：

1. **绩效考核**：试用期员工不参与常规季度/年度绩效考核。根据资料5第5.1条，入职不满2个月不参与当季考核；考核自下一个完整季度起算。且资料5第5.2条明确，试用期员工在转正评估时使用单独的《转正评估表》，不适用常规绩效评级（如S/A/B/C/D）。

2. **转正评估**：
- 启动时点：试用期届满前10个工作日启动（资料2第3.1条、资料3第六问）；
- 流程：员工提交申请与总结 → 直属主管填写《转正评估表》→ 部门负责人审核 → 人力资源部复核 → 结论于届满前3个工作日反馈（资料2第3.2–3.6条）；
- 评分维度：业绩达成、专业能力、协作、价值观，各占25%（即各25分，满分100分）（资料1第7.1条、资料2第3.3条、资料3第7.1条）；
- 结论判定：80分及以上为“胜任”，60–79分为“基本胜任”，60分以下为“不胜任”；任一维度得分低于该维度满分50%（即<12.5分）则不得评为“胜任”；出现合规红线行为直接评为“不胜任”（资料1第7.2–7.4条）；
- 特殊情形：可提前转正（入职满2个月且业绩突出，经批准）；评估为“基本胜任”可延长试用期1次、不超过1个月；请假超5个工作日则评估日期顺延（资料2第4.1–4.5条、资料3第4.1–4.5条）。

引用：新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 绩效考核管理办法.md

人工结论：待复核

### HR-33 我要离职了，交接和竞业限制分别有什么要求？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：离职管理与工作交接流程.md, 离职证明与竞业限制说明.md

检索来源：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 离职管理与工作交接流程.md, 离职证明与竞业限制说明.md, 离职管理与工作交接流程.md

参考：正式员工须提前 30 日书面通知并完成工作交接；竞业限制只有在劳动合同或专项协议中明确约定才适用，未约定则不适用。

实际：交接要求：员工须在最后工作日前完成全部交接，内容包括业务事项（在办项目、客户联系人等）、文档资料（需求文档、账号密码等）、系统权限（代码仓库、生产环境等）、资产设备（笔记本电脑、工牌等）及财务事项（未报销单据、预借款等）；交接须签署《工作交接单》，由交接人、接收人与直属主管三方签字；未完成交接的，公司可暂缓出具离职证明并暂扣离职结算款。竞业限制要求：仅适用于劳动合同或专项协议中明确约定的核心岗位员工（如核心技术研发岗P6及以上、关键客户负责人、高级管理人员M3及以上）；竞业限制期限最长不超过12个月，自离职之日起算；公司须按离职前12个月平均工资的30%按月支付补偿金（每月15日发放）；员工在竞业限制期内不得入职竞争企业或自营同类业务；公司未按约定支付补偿金超过3个月的，员工可请求解除该约定。

引用：离职证明与竞业限制说明.md, 离职管理与工作交接流程.md, 离职证明与竞业限制说明.md

人工结论：待复核

### HR-34 一张 26000 元的差旅报销单要走到哪一级审批？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：费用报销审批权限表.md, 差旅报销标准（一线城市）.md

检索来源：费用报销审批权限表.md, 费用报销审批权限表.md, 费用报销审批权限表.md, 报销与出差常见问题 FAQ.md, 费用报销审批权限表.md

参考：单笔 20000 元（含）以上，须由分管副总、财务负责人与总经理审批。

实际：一张 26000 元的差旅报销单属于 20000 元（含）以上档，需由分管副总、财务负责人与总经理审批。

引用：费用报销审批权限表.md, 费用报销审批权限表.md, 报销与出差常见问题 FAQ.md, 费用报销审批权限表.md

人工结论：待复核

### HR-35 公司有没有员工期权或股权激励计划？行权价格怎么定？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：职级体系与薪资带宽表.md, 年终奖与绩效奖金发放办法.md, 绩效考核管理办法.md, 节日福利与团建经费管理办法.md, 年终奖与绩效奖金发放办法.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-36 员工的子女教育补贴标准是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：节日福利与团建经费管理办法.md, 职级体系与薪资带宽表.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md, 年终奖与绩效奖金发放办法.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-37 公司有没有通勤班车？班车路线和发车时间是怎么规定的？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：星桥科技员工手册（总则）.md, 考勤管理与打卡规范.md, 弹性工作制实施细则.md, 考勤管理与打卡规范.md, 日常费用报销管理办法.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-38 公司提供员工宿舍或者住房补贴吗？标准是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：报销与出差常见问题 FAQ.md, 员工入职办理指南.md, 节日福利与团建经费管理办法.md, 社会保险与住房公积金管理办法.md, 职级体系与薪资带宽表.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-39 常驻海外的派驻补贴标准是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：出差管理办法.md, 出差管理办法.md, 出差管理办法.md, 关于调整 2026 年度差旅住宿标准的通知.md, 报销与出差常见问题 FAQ.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-40 公司有企业年金计划吗？缴费比例是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：社会保险与住房公积金管理办法.md, 补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-41 员工购车补贴和油卡福利怎么申请？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：节日福利与团建经费管理办法.md, 星桥科技员工手册（总则）.md, 日常费用报销管理办法.md, 报销与出差常见问题 FAQ.md, 补充医疗保险与年度体检福利说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-42 公司有没有托育服务或母婴室？使用规则是什么？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：请假与休假管理制度.md, 星桥科技员工手册（总则）.md, 请假与休假管理制度.md, 关于启用新版考勤与请假制度的通知.md, 社会保险与住房公积金管理办法.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-43 弹性福利自选平台的积分额度是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：关于启用新版考勤与请假制度的通知.md, 节日福利与团建经费管理办法.md, 弹性工作制实施细则.md, 职级体系与薪资带宽表.md, 节日福利与团建经费管理办法.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-44 员工内部创业和项目孵化支持政策是怎么规定的？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：节日福利与团建经费管理办法.md, 培训管理办法.md, 节日福利与团建经费管理办法.md, 星桥科技员工手册（总则）.md, 弹性工作制实施细则.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-45 生育津贴的具体计算公式是什么？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：年终奖与绩效奖金发放办法.md, 请假类型与假期额度对照表.md, 餐饮与团建费用报销口径.md, 职级体系与薪资带宽表.md, 绩效评级与结果应用说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-46 加班超过每月 36 小时上限后，具体的处罚金额是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：加班与调休管理办法.md, 加班与调休管理办法.md, 职级体系与薪资带宽表.md, 值班与加班补贴说明.md, 已废止制度清单与替代关系说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-47 竞业限制违约金的计算基数是哪个月的工资？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 职级体系与薪资带宽表.md, 年终奖与绩效奖金发放办法.md

参考：（无）

实际：竞业限制违约金的计算基数不是某个月的工资，而是约定的竞业限制补偿金总额。根据资料，违约金标准为约定补偿金总额的3倍（见4.4条及7.4条示例）。而补偿金的计算基数才是离职前12个月的平均工资（见3.1、3.2条）。

引用：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 职级体系与薪资带宽表.md

人工结论：待复核

### HR-48 年度调薪的最终百分比由谁审批确定？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：绩效评级与结果应用说明.md, 职级体系与薪资带宽表.md, 绩效评级与结果应用说明.md, 绩效考核管理办法.md, 薪酬结构与发薪日历说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-49 体检报告异常后的复查费用能报销多少比例？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md, 报销与出差常见问题 FAQ.md, 补充医疗保险与年度体检福利说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-50 申诉调查中引入外部顾问的费用上限是多少？

难度：refusal ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：员工申诉与投诉处理流程.md, 补充医疗保险与年度体检福利说明.md, 报销与出差常见问题 FAQ.md, 采购与付款审批权限表.md, 员工关系与假期常见问题 FAQ.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-51 IT 部门一位同事问：标准工时下的上班打卡有效窗口是几点到几点？

难度：cross_kb ｜ 库：hr ｜ split：dev

标注来源：（期望拒答）

检索来源：VPN 使用指南（北京）.md, 办公终端配置标准.md, 办公终端配置标准.md, 无线网络接入与访客 Wi-Fi 管理办法.md, 终端安全检查与补丁管理规范.md

参考：上班打卡有效窗口为 08:30 至 10:00，10:00 之后视为迟到。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-52 IT 运维同事问：周末值班的补贴标准是多少？

难度：cross_kb ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：VPN 使用指南（北京）.md, 数据备份策略与恢复演练规范.md, Wi-Fi 认证方式升级通知.md, Wi-Fi 认证方式升级通知.md, 打印机安装与驱动配置手册.md

参考：休息日值班 300 元/次，不折算调休。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-53 IT 部门 HRBP 咨询：员工每年带薪病假有几天？

难度：cross_kb ｜ 库：hr ｜ split：dev

标注来源：（期望拒答）

检索来源：数据备份策略与恢复演练规范.md, 终端设备领用与归还登记表.md, 权限申请与最小权限矩阵.md, 数据备份策略与恢复演练规范.md, IT 系统变更与版本记录.md

参考：每年 5 天带薪病假，超出部分按本人日工资的 60% 计发。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-54 产品经理问：去杭州出差住宿每晚最多能报销多少？

难度：cross_kb ｜ 库：hr ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议常见问题 FAQ.md, 星桥会议常见问题 FAQ.md, 星桥科技服务等级协议 SLA 总则.md, 星桥科技统一计费与续费口径说明.md, 星桥会议套餐配额与并发说明.md

参考：450 元/晚（杭州属于其他城市）。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-55 产品团队同事问：婚假有多少天？

难度：cross_kb ｜ 库：hr ｜ split：dev

标注来源：（期望拒答）

检索来源：星桥工单 SLA 分级与响应时限.md, 星桥云盘数据备份与保留策略.md, 星桥会议接口接入与鉴权指南.md, 星桥云盘开放接口接入指南.md, 星桥会议录制与存储保留策略.md

参考：婚假 10 个自然日，须在领证之日起 12 个月内休完。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### HR-56 产品部门问：团建经费每人每季度是多少钱？

难度：cross_kb ｜ 库：hr ｜ split：dev

标注来源：（期望拒答）

检索来源：星桥科技统一计费与续费口径说明.md, 星桥会议套餐配额与并发说明.md, 星桥会议套餐配额与并发说明.md, 星桥云盘套餐与配额对照表.md, 星桥云盘套餐与配额对照表.md

参考：每人每季度 200 元，全年每人累计不超过 800 元。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-01 公司 IT 服务台的分机号是多少？

难度：easy ｜ 库：it ｜ split：test

标注来源：VPN 使用指南（北京）.md

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, 打印机安装与驱动配置手册.md, VPN 客户端故障排查清单.md, 密码找回与重置流程 FAQ.md, 邮件误发与撤回应急处理指引.md

参考：分机 6001。

实际：公司 IT 服务台的分机号是 6001。

引用：无线网络接入与访客 Wi-Fi 管理办法.md, 打印机安装与驱动配置手册.md, VPN 客户端故障排查清单.md, 密码找回与重置流程 FAQ.md, 邮件误发与撤回应急处理指引.md

人工结论：待复核

### IT-02 连接内网时客户端报错误码 691，一般是哪里出了问题？

难度：easy ｜ 库：it ｜ split：dev

标注来源：VPN 客户端故障排查清单.md

检索来源：办公网络端口与服务清单.md, VPN 客户端故障排查清单.md, 无线信号弱与频繁掉线排查清单.md, 办公网络端口与服务清单.md, 无线信号弱与频繁掉线排查清单.md

参考：用户名或密码错误，需要核对凭据的大小写与输入法。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-03 协同盘里被删掉的文件在回收站能放多久？

难度：easy ｜ 库：it ｜ split：dev

标注来源：共享盘目录结构与权限规范.md

检索来源：共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md

参考：回收站保留 30 天。

实际：协同盘里被删掉的文件在回收站能保留30天。

引用：共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md

人工结论：待复核

### IT-04 来访客户用的 Wi-Fi 通行码能用多长时间？

难度：easy ｜ 库：it ｜ split：test

标注来源：无线网络接入与访客 Wi-Fi 管理办法.md

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, 无线网络接入与访客 Wi-Fi 管理办法.md, 无线网络接入与访客 Wi-Fi 管理办法.md, VPN 使用指南（北京）.md, VPN 使用指南（上海）.md

参考：通行码有效期 6 小时，过期不延期。

实际：来访客户用的 Wi-Fi 通行码有效期为 6 小时，过期后自动失效，不提供延期。

引用：无线网络接入与访客 Wi-Fi 管理办法.md, 无线网络接入与访客 Wi-Fi 管理办法.md, 无线网络接入与访客 Wi-Fi 管理办法.md

人工结论：待复核

### IT-05 打印黑白单面一页要收多少钱？

难度：easy ｜ 库：it ｜ split：dev

标注来源：打印计费与耗材申领规定.md

检索来源：打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印机安装与驱动配置手册.md, 打印机安装与驱动配置手册.md

参考：黑白单面 0.05 元/页。

实际：打印黑白单面一页收取0.05元。

引用：打印计费与耗材申领规定.md

人工结论：待复核

### IT-06 发现信息安全事件时的应急电话是多少？

难度：easy ｜ 库：it ｜ split：dev

标注来源：信息安全事件分级与上报流程.md

检索来源：信息安全事件分级与上报流程.md, 邮件误发与撤回应急处理指引.md, 信息安全事件分级与上报流程.md, 信息安全事件分级与上报流程.md, 密码找回与重置流程 FAQ.md

参考：分机 6001，全年可拨。

实际：发现信息安全事件时的应急电话是分机6001。

引用：信息安全事件分级与上报流程.md, 邮件误发与撤回应急处理指引.md, 信息安全事件分级与上报流程.md, 信息安全事件分级与上报流程.md

人工结论：待复核

### IT-07 新员工入职后的域账号一般多久能开通好？

难度：easy ｜ 库：it ｜ split：test

标注来源：AD 域账号与权限管理规定.md

检索来源：AD 域账号与权限管理规定.md, 密码找回与重置流程 FAQ.md, 域账号锁定与解锁自助指南.md, AD 域账号与权限管理规定.md, 域账号锁定与解锁自助指南.md

参考：收到入职名单后 4 小时内完成主账号创建。

实际：新员工入职后的域账号一般在人力资源部推送入职名单后4小时内开通好。

引用：AD 域账号与权限管理规定.md, AD 域账号与权限管理规定.md

人工结论：待复核

### IT-08 会议室屏幕上显示的投屏码多久会失效？

难度：easy ｜ 库：it ｜ split：dev

标注来源：会议室音视频设备使用手册.md

检索来源：会议室音视频设备使用手册.md, 会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md, 会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md

参考：投屏码有效期 2 分钟，超时需重新获取。

实际：会议室屏幕上显示的投屏码有效期为2分钟。

引用：会议室音视频设备使用手册.md, 会议室音视频设备使用手册.md

人工结论：待复核

### IT-09 手机上那个每次刷新的动态数字，连续输错会被停多久？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：多因素认证（MFA）操作手册.md

检索来源：多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, Wi-Fi 认证方式升级通知.md, 域账号锁定与解锁自助指南.md, Wi-Fi 认证方式升级通知.md

参考：连续 5 次错误会锁定 10 分钟。

实际：连续输错 5 次会被锁定 10 分钟。

引用：多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md

人工结论：待复核

### IT-10 在北京家里办公时，一次远程连接最长能挂多久就必须重新认证？

难度：paraphrase ｜ 库：it ｜ split：test

标注来源：VPN 使用指南（北京）.md

检索来源：VPN 使用指南（北京）.md, Wi-Fi 认证方式升级通知.md, 远程接入与零信任管理办法.md, 远程接入与零信任管理办法.md, 域账号锁定与解锁自助指南.md

参考：单次连接最长 8 小时，达到后自动断开。

实际：在北京家里办公时，一次远程连接最长能挂8小时就必须重新认证。

引用：VPN 使用指南（北京）.md, 远程接入与零信任管理办法.md

人工结论：待复核

### IT-11 华东区同事走上海通道，单次连接可以连续用多长时间？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：VPN 使用指南（上海）.md

检索来源：VPN 使用指南（上海）.md, VPN 使用指南（上海）.md, 远程接入与零信任管理办法.md, VPN 使用指南（北京）.md, VPN 使用指南（上海）.md

参考：单次连接最长 12 小时。

实际：华东区同事走上海通道，单次连接可以连续使用12小时。

引用：VPN 使用指南（上海）.md, 远程接入与零信任管理办法.md, VPN 使用指南（上海）.md

人工结论：待复核

### IT-12 发邮件时最多能带多大的附件？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：企业邮箱使用手册.md

检索来源：企业邮箱容量与附件限制说明.md, 企业邮箱容量与附件限制说明.md, 企业邮箱使用手册.md, 企业邮箱容量与附件限制说明.md, 扫描到邮箱与共享盘操作指南.md

参考：单封邮件附件累计不超过 25 MB。

实际：发邮件时单封邮件附件累计大小最多为25 MB；外包驻场账号为10 MB。超过该限制需使用超大附件链接机制，单个超大附件文件最大支持5 GB。

引用：企业邮箱容量与附件限制说明.md, 企业邮箱使用手册.md

人工结论：待复核

### IT-13 内部邮件发错人了，还能在多长时间内点撤回？

难度：paraphrase ｜ 库：it ｜ split：test

标注来源：邮件误发与撤回应急处理指引.md

检索来源：邮件误发与撤回应急处理指引.md, 邮件误发与撤回应急处理指引.md, 邮件误发与撤回应急处理指引.md, 密码复杂度与锁定策略规范.md, 企业邮箱容量与附件限制说明.md

参考：内部邮件撤回窗口为发出后 2 分钟内，外部邮件不支持撤回。

实际：内部邮件发错人后，可在发出后2分钟内点撤回。超过2分钟系统不支持撤回。

引用：邮件误发与撤回应急处理指引.md, 邮件误发与撤回应急处理指引.md

人工结论：待复核

### IT-14 打印完忘了拿，材料会在机器里留多久？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：打印机安装与驱动配置手册.md

检索来源：打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 终端设备领用与归还登记表.md

参考：打印任务保留 2 小时，超时自动清除。

实际：材料会在机器里保留2小时，超过2小时未取将自动清除，且仍会计费，不退还计费额度。

引用：打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md

人工结论：待复核

### IT-15 往公司外面发文件，超过多大就得先让部门负责人点头？

难度：paraphrase ｜ 库：it ｜ split：test

标注来源：文件协作与外发审批办法.md

检索来源：文件协作与外发审批办法.md, 文件协作与外发审批办法.md, 文件协作与外发审批办法.md, 扫描到邮箱与共享盘操作指南.md, 企业邮箱使用手册.md

参考：外发文件超过 50 MB 需部门负责人审批。

实际：超过50 MB就得先让部门负责人点头。

引用：文件协作与外发审批办法.md, 文件协作与外发审批办法.md

人工结论：待复核

### IT-16 公司配的笔记本，电池至少要能撑多久才算达标？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：办公终端配置标准.md

检索来源：办公终端配置标准.md, 办公终端配置标准.md, 办公终端配置标准.md, 终端设备领用与归还登记表.md, 终端安全检查与补丁管理规范.md

参考：电池续航不低于 6 小时。

实际：公司配的笔记本，电池续航不低于6小时（标准办公场景实测）才算达标。

引用：办公终端配置标准.md, 办公终端配置标准.md

人工结论：待复核

### IT-17 客户名单这种材料想直接打印出来，要先办什么手续？

难度：paraphrase ｜ 库：it ｜ split：dev

标注来源：打印机安装与驱动配置手册.md

检索来源：打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md, 常用软件自助安装指引.md, 打印计费与耗材申领规定.md, 打印机安装与驱动配置手册.md

参考：必须先走《文件协作与外发审批办法》，禁止直接打印客户名单。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-18 换了新手机以后，令牌绑定要在多长时间内弄完？

难度：paraphrase ｜ 库：it ｜ split：test

标注来源：多因素认证（MFA）操作手册.md

检索来源：多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, Wi-Fi 认证方式升级通知.md, 密码找回与重置流程 FAQ.md

参考：新手机绑定需 30 分钟内完成扫码与验证。

实际：换了新手机以后，令牌绑定需在30分钟内完成。

引用：多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md

人工结论：待复核

### IT-19 域账号密码连续输错几次会被锁？锁多久？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：域账号锁定与解锁自助指南.md

检索来源：域账号锁定与解锁自助指南.md, 域账号锁定与解锁自助指南.md, 密码找回与重置流程 FAQ.md, 密码复杂度与锁定策略规范.md, 域账号锁定与解锁自助指南.md

参考：连续 6 次密码错误锁定 15 分钟，到期自动解锁。

实际：域账号密码连续输错6次会被锁定，锁定时长为15分钟，之后系统自动解锁。

引用：域账号锁定与解锁自助指南.md, 域账号锁定与解锁自助指南.md, 密码复杂度与锁定策略规范.md, 域账号锁定与解锁自助指南.md

人工结论：待复核

### IT-20 邮箱密码连续输错几次会锁？锁上之后能自己等到解锁吗？

难度：numeric ｜ 库：it ｜ split：test

标注来源：企业邮箱使用手册.md

检索来源：密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md, 账号锁定与解锁自助指南.md, 域账号锁定与解锁自助指南.md, 域账号锁定与解锁自助指南.md

参考：连续 3 次锁定，且不设自动解锁时长，需致电服务台人工解锁。

实际：企业邮箱密码连续输错3次会锁定，且不设自动解锁时长，无法自己等到解锁，必须致电分机6001由服务台人工解锁。

引用：密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md

人工结论：待复核

### IT-21 无线网络认证连续失败几次会被临时挡住？挡多长时间？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：无线网络接入与访客 Wi-Fi 管理办法.md

检索来源：Wi-Fi 认证方式升级通知.md, 无线信号弱与频繁掉线排查清单.md, 无线信号弱与频繁掉线排查清单.md, Wi-Fi 认证方式升级通知.md, 多因素认证（MFA）操作手册.md

参考：连续 4 次认证失败锁定 20 分钟，到期自动解锁。

实际：无线网络认证连续失败4次会被临时锁定，锁定时长为20分钟。

引用：Wi-Fi 认证方式升级通知.md, 无线信号弱与频繁掉线排查清单.md, 无线信号弱与频繁掉线排查清单.md

人工结论：待复核

### IT-22 公司对密码长度最低要求是多少位？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：密码复杂度与锁定策略规范.md

检索来源：密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md, VPN 使用指南（上海）.md, 密码复杂度与锁定策略规范.md

参考：长度不少于 12 位。

实际：公司对密码长度最低要求是12位。

引用：密码复杂度与锁定策略规范.md

人工结论：待复核

### IT-23 员工主账号的密码多久必须换一次？

难度：numeric ｜ 库：it ｜ split：test

标注来源：密码复杂度与锁定策略规范.md

检索来源：密码复杂度与锁定策略规范.md, 密码复杂度与锁定策略规范.md, 密码找回与重置流程 FAQ.md, 密码复杂度与锁定策略规范.md, 密码找回与重置流程 FAQ.md

参考：每 90 天更换一次。

实际：员工主账号的密码必须每90天更换一次。

引用：密码复杂度与锁定策略规范.md, 密码找回与重置流程 FAQ.md, 密码找回与重置流程 FAQ.md

人工结论：待复核

### IT-24 公司邮箱给正式员工分配多少容量？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：企业邮箱容量与附件限制说明.md

检索来源：企业邮箱使用手册.md, 企业邮箱容量与附件限制说明.md, 企业邮箱容量与附件限制说明.md, 企业邮箱使用手册.md, 企业邮箱容量与附件限制说明.md

参考：正式员工邮箱容量 50 GB。

实际：公司邮箱给正式员工分配的容量为50 GB。

引用：企业邮箱使用手册.md, 企业邮箱容量与附件限制说明.md

人工结论：待复核

### IT-25 全量备份和增量备份分别保留多久？

难度：numeric ｜ 库：it ｜ split：test

标注来源：数据备份策略与恢复演练规范.md

检索来源：数据备份策略与恢复演练规范.md, 数据备份策略与恢复演练规范.md, 共享盘目录结构与权限规范.md, IT 系统变更与版本记录.md, 文件误删恢复申请指引.md

参考：全量保留 8 周，增量保留 30 天。

实际：全量备份保留期：一级系统（协同盘、邮件系统、代码库）为8周，二级系统（工单系统、办公门户）为4周；增量备份保留期：一级系统为30天，二级系统为14天。

引用：数据备份策略与恢复演练规范.md, 数据备份策略与恢复演练规范.md

人工结论：待复核

### IT-26 高危补丁要求在多长时间内装完？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：终端安全检查与补丁管理规范.md

检索来源：终端安全检查与补丁管理规范.md, 终端安全检查与补丁管理规范.md, 办公终端配置标准.md, 远程接入与零信任管理办法.md, 软件安装申请与审批流程.md

参考：发布后 72 小时内完成。

实际：高危补丁要求在72小时内安装完成。

引用：终端安全检查与补丁管理规范.md, 终端安全检查与补丁管理规范.md

人工结论：待复核

### IT-27 个人办公终端默认的下行限速是多少？

难度：numeric ｜ 库：it ｜ split：dev

标注来源：网络带宽使用与限速规定.md

检索来源：网络带宽使用与限速规定.md, VPN 使用指南（北京）.md, 网络带宽使用与限速规定.md, 办公终端配置标准.md, 网络带宽使用与限速规定.md

参考：个人终端默认下行限速 100 Mbps。

实际：个人办公终端默认的下行限速是100 Mbps。

引用：网络带宽使用与限速规定.md, 网络带宽使用与限速规定.md

人工结论：待复核

### IT-28 彩色打印一页收多少钱？

难度：numeric ｜ 库：it ｜ split：test

标注来源：打印计费与耗材申领规定.md

检索来源：打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印计费与耗材申领规定.md, 打印机安装与驱动配置手册.md, 打印机安装与驱动配置手册.md

参考：彩色单面 0.35 元/页。

实际：彩色打印一页收费0.35元（单面）或0.60元（双面），需手动选择彩色模式。

引用：打印计费与耗材申领规定.md

人工结论：待复核

### IT-29 我在家想打开部门共享盘，网络连上以外还差什么条件？

难度：multi_source ｜ 库：it ｜ split：test

标注来源：远程接入与零信任管理办法.md, 共享盘目录结构与权限规范.md

检索来源：共享盘目录结构与权限规范.md, 有线接入与交换机端口登记表.md, 无线信号弱与频繁掉线排查清单.md, 办公网络端口与服务清单.md, 企业邮箱使用手册.md

参考：需通过零信任设备合规检查，且部门目录默认已按部门授权；跨部门项目目录需项目负责人提交成员名单。

实际：除了网络连接，还需先接入公司VPN，并通过零信任设备的合规检查，才能访问部门共享盘。

引用：共享盘目录结构与权限规范.md

人工结论：待复核

### IT-30 密码忘了、手机令牌也不能用，人工重置要核验什么？临时密码能活多久？

难度：multi_source ｜ 库：it ｜ split：dev

标注来源：密码找回与重置流程 FAQ.md, 多因素认证（MFA）操作手册.md

检索来源：密码找回与重置流程 FAQ.md, 多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, 多因素认证（MFA）操作手册.md, 密码找回与重置流程 FAQ.md

参考：先致电 6001 冻结令牌，再完成身份核验（工牌或工号、预留手机号、主管确认任两项）；核验后发放临时密码，有效期 2 小时且首次登录必须修改。

实际：人工重置需核验以下任两项：工牌或工号、入职登记时预留的手机号接收验证短信、直属主管在工单中的书面确认。临时密码有效期为2小时。

引用：密码找回与重置流程 FAQ.md

人工结论：待复核

### IT-31 用一体机扫描的文件默认发到哪？太大发不出去怎么办？

难度：multi_source ｜ 库：it ｜ split：test

标注来源：扫描到邮箱与共享盘操作指南.md, 企业邮箱容量与附件限制说明.md

检索来源：扫描到邮箱与共享盘操作指南.md, 扫描到邮箱与共享盘操作指南.md, 扫描到邮箱与共享盘操作指南.md, 扫描到邮箱与共享盘操作指南.md, 打印机安装与驱动配置手册.md

参考：默认发送至本人企业邮箱；超过 25 MB 时邮件系统提示改用超大附件链接。

实际：用一体机扫描的文件默认发到本人企业邮箱；若文件过大（超过20 MB）导致发送失败，系统会自动转存至共享盘临时目录，需在24小时内手动转存。也可提前选择「扫描到共享盘」方式，单份上限为50 MB。

引用：扫描到邮箱与共享盘操作指南.md, 扫描到邮箱与共享盘操作指南.md

人工结论：待复核

### IT-32 员工离职时，账号和办公电脑分别在什么时候处理完？

难度：multi_source ｜ 库：it ｜ split：dev

标注来源：离职与转岗账号回收流程.md, 终端设备领用与归还登记表.md

检索来源：离职与转岗账号回收流程.md, 离职与转岗账号回收流程.md, 离职与转岗账号回收流程.md, 离职与转岗账号回收流程.md, 终端设备领用与归还登记表.md

参考：账号在离职当日 18:00 前禁用并完成令牌注销与 VPN 权限回收；办公终端最迟在离职后 5 个工作日内归还。

实际：员工离职时，账号须在离职当日18:00前完成禁用（含令牌注销、VPN权限回收）；办公电脑（终端设备）须在离职后5个工作日内归还。

引用：离职与转岗账号回收流程.md, 离职与转岗账号回收流程.md, 终端设备领用与归还登记表.md

人工结论：待复核

### IT-33 会议开到一半投屏断了，按文档应该怎么应急？

难度：multi_source ｜ 库：it ｜ split：dev

标注来源：会议室音视频设备使用手册.md, 会议室预约与设备故障报备 FAQ.md

检索来源：会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md, 会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md, 无线信号弱与频繁掉线排查清单.md

参考：改用有线连接作为应急方案；必要时断电重启投屏器并致电 6001 申请调换会议室。

实际：根据文档，会议中投屏断开属于「三级故障」（投屏码无效、单屏无画面），应按以下步骤应急：1. 立即改用有线连接作为应急方案；2. 检查投屏器是否过热，必要时断电60秒后重启；3. 若5分钟内无法恢复，致电分机6001请求调换会议室。同时，会中报备以「保障会议可继续」为第一目标，需按模板提供会议室编号、故障现象、已尝试步骤等信息。

引用：会议室预约与设备故障报备 FAQ.md, 会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md

人工结论：待复核

### IT-34 协同盘里的文件被误删，回收站也已经过期，还能从哪里找回？

难度：multi_source ｜ 库：it ｜ split：test

标注来源：文件误删恢复申请指引.md, 数据备份策略与恢复演练规范.md

检索来源：文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 共享盘目录结构与权限规范.md, 共享盘目录结构与权限规范.md

参考：删除超过 30 天需由系统与账号组从备份副本恢复；一级系统另有保留 90 天的异地副本。

实际：当协同盘文件被误删且回收站已过期（超过30天）时，若文件删除未超过90天，可尝试通过「版本历史」还原；若已超过90天，则需提交「文件误删恢复」IT工单，由系统与账号组从备份副本恢复（处理时限为3个工作日）。但若删除已超过90天且无可用备份，则无法恢复。

引用：文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 文件误删恢复申请指引.md, 共享盘目录结构与权限规范.md

人工结论：待复核

### IT-35 星桥科技员工每年能休多少天年假？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：AD 域账号与权限管理规定.md, 办公终端配置标准.md, 权限申请与最小权限矩阵.md, IT 系统变更与版本记录.md, 密码复杂度与锁定策略规范.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-36 公司今年春节的放假安排是怎么定的？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：it-exit-account-revocation.pdf, 密码复杂度与锁定策略规范.md, 日历共享与会议室预订 FAQ.md, 数据备份策略与恢复演练规范.md, it-vpn-lockout-policy.pdf

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-37 公司提供餐补吗？食堂几点开饭？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：Wi-Fi 认证方式升级通知.md, 会议室预约与设备故障报备 FAQ.md, 会议室预约与设备故障报备 FAQ.md, 无线网络接入与访客 Wi-Fi 管理办法.md, 打印机安装与驱动配置手册.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-38 办公楼停车位是怎么收费的？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：打印机安装与驱动配置手册.md, 日历共享与会议室预订 FAQ.md, 办公终端配置标准.md, 软件安装申请与审批流程.md, 有线接入与交换机端口登记表.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-39 公司健身房每天开放到几点？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：VPN 使用指南（北京）.md, 会议室预约与设备故障报备 FAQ.md, Wi-Fi 认证方式升级通知.md, VPN 使用指南（北京）.md, 日历共享与会议室预订 FAQ.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-40 星桥科技的股票期权行权价格是多少？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：正版软件授权与 License 台账.md, AD 域账号与权限管理规定.md, 密码复杂度与锁定策略规范.md, 办公终端配置标准.md, 网络带宽使用与限速规定.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-41 公司给供应商付款的账期是多少天？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：正版软件授权与 License 台账.md, 终端设备领用与归还登记表.md, 数据备份策略与恢复演练规范.md, 文件协作与外发审批办法.md, 打印计费与耗材申领规定.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-42 出差住宿费的报销上限是多少？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, VPN 使用指南（北京）.md, VPN 使用指南（上海）.md, 日历共享与会议室预订 FAQ.md, 无线网络接入与访客 Wi-Fi 管理办法.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-43 星桥协同盘企业版对外售价是多少？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：共享盘目录结构与权限规范.md, 办公终端配置标准.md, 正版软件授权与 License 台账.md, 网络带宽使用与限速规定.md, 文件协作与外发审批办法.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-44 公司办公楼多久组织一次消防演练？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：数据备份策略与恢复演练规范.md, 数据备份策略与恢复演练规范.md, 会议室音视频设备使用手册.md, 无线信号弱与频繁掉线排查清单.md, Wi-Fi 认证方式升级通知.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-45 北京 VPN 节点使用的隧道加密算法是哪一种？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：远程接入与零信任管理办法.md, VPN 使用指南（北京）.md, 远程接入与零信任管理办法.md, VPN 使用指南（上海）.md, 多因素认证（MFA）操作手册.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-46 打印一体机使用的墨盒型号是什么？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：打印机安装与驱动配置手册.md, 打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md, 打印机安装与驱动配置手册.md, 打印计费与耗材申领规定.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-47 公司根证书的有效期是几年？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：正版软件授权与 License 台账.md, 正版软件授权与 License 台账.md, AD 域账号与权限管理规定.md, 权限申请与最小权限矩阵.md, 正版软件授权与 License 台账.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-48 IT 服务台值班人员的名单和工号在哪里能查到？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, VPN 客户端故障排查清单.md, 办公网络端口与服务清单.md, 密码找回与重置流程 FAQ.md, 打印机安装与驱动配置手册.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-49 会议室摄像头的最大光学变焦倍数是多少？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：会议室预约与设备故障报备 FAQ.md, 会议室音视频设备使用手册.md, 日历共享与会议室预订 FAQ.md, 会议室音视频设备使用手册.md, 扫描到邮箱与共享盘操作指南.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-50 共享盘单文件超过 5 GB 时，官方建议怎么拆分？

难度：refusal ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：共享盘目录结构与权限规范.md, 共享盘目录结构与权限规范.md, 扫描到邮箱与共享盘操作指南.md, 共享盘目录结构与权限规范.md, 扫描到邮箱与共享盘操作指南.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-51 新人入职当天人事已经提报名单了，我这边邮箱多久能用上？

难度：cross_kb ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：员工入职办理指南.md, 员工入职办理指南.md, 员工关系与假期常见问题 FAQ.md, 员工入职办理指南.md, 用章与合同审批权限表.md

参考：收到名单后 4 小时内完成主账号创建，并同步开通邮箱与工单系统。

实际：入职当天10:30至11:00完成邮箱开通，因此报到当日即可使用邮箱。

引用：员工入职办理指南.md, 员工入职办理指南.md

人工结论：待复核

### IT-52 员工离职当天，公司账号和相关权限什么时候停掉？

难度：cross_kb ｜ 库：it ｜ split：dev

标注来源：（期望拒答）

检索来源：离职管理与工作交接流程.md, 离职管理与工作交接流程.md, 离职管理与工作交接流程.md, 离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md

参考：离职当日 18:00 前完成账号禁用、令牌注销与 VPN 权限回收。

实际：公司账号和相关权限应在员工最后工作日当天完成注销与回收。具体包括：邮箱与系统账号注销、企业微信退出；涉及核心系统权限的岗位，信息技术部须在最后工作日18:00前完成权限回收。

引用：离职管理与工作交接流程.md, 离职证明与竞业限制说明.md

人工结论：待复核

### IT-53 实习生和外包驻场人员的账号最长能用到多久？

难度：cross_kb ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：新员工试用期管理与转正流程.md, 员工关系与假期常见问题 FAQ.md, 培训管理办法.md, 请假类型与假期额度对照表.md, 员工关系与假期常见问题 FAQ.md

参考：实习生账号最长 6 个月，外包驻场账号最长 3 个月。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-54 客户问协同盘个人空间有多大、单个文件能传多大？

难度：cross_kb ｜ 库：it ｜ split：dev

标注来源：（期望拒答）

检索来源：星桥云盘账号与共享授权说明.md, 星桥会议与云盘集成说明.md, 星桥云盘数据导入导出操作指南.md, 星桥会议套餐配额与并发说明.md, 星桥云盘账号与共享授权说明.md

参考：个人目录配额 20 GB，单个文件不超过 5 GB。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-55 客户想了解会议室投屏，投屏码有效期是多久？

难度：cross_kb ｜ 库：it ｜ split：dev

标注来源：（期望拒答）

检索来源：星桥会议接口接入与鉴权指南.md, 星桥科技统一计费与续费口径说明.md, 星桥科技统一账号与单点登录说明.md, 星桥会议常见问题 FAQ.md, 星桥科技统一计费与续费口径说明.md

参考：投屏码有效期 2 分钟，超时需重新获取。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### IT-56 客户问公司邮箱的附件上限，以及超大附件链接能挂多久？

难度：cross_kb ｜ 库：it ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单常见问题 FAQ.md, 星桥工单产品功能手册.md, 星桥云盘开放接口接入指南.md, 星桥云盘套餐与配额对照表.md, 星桥云盘产品功能手册.md

参考：单封邮件附件累计不超过 25 MB，超大附件链接有效期 14 天。

实际：公司邮箱的附件单个上限为50 MB，单工单累计上限为200 MB。超大附件需使用云盘链接，外链有效期支持7天、30天或永久（仅旗舰版支持永久外链）。

引用：星桥工单常见问题 FAQ.md, 星桥工单产品功能手册.md, 星桥云盘产品功能手册.md

人工结论：待复核

### PD-01 我们往星桥云盘传一个 30 GB 的备份包一直失败，云盘单文件最大能到多少？

难度：easy ｜ 库：product ｜ split：test

标注来源：星桥云盘产品功能手册.md

检索来源：星桥云盘错误码说明.md, 星桥云盘产品功能手册.md, 星桥云盘套餐与配额对照表.md, 星桥云盘产品功能手册.md, 星桥云盘套餐与配额对照表.md

参考：单文件最大 20 GB；超过 200 MB 的文件会自动走分片上传，分片大小默认 8 MB，超过 20 GB 只能分卷压缩后重传。

实际：星桥云盘单文件最大为 20 GB，30 GB 的备份包已超出上限，需分卷压缩后重传。

引用：星桥云盘错误码说明.md, 星桥云盘套餐与配额对照表.md

人工结论：待复核

### PD-02 同事误删了云盘里的文件，回收站能放多久还能找回来？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥云盘产品功能手册.md

检索来源：星桥会议录制与存储保留策略.md, 星桥云盘数据备份与保留策略.md, 星桥会议录制与存储保留策略.md, 星桥云盘产品功能手册.md, 星桥云盘数据备份与保留策略.md

参考：删除的文件进入回收站后保留 30 天，普通成员可自助恢复；超过保留期进入清理队列，物理删除后无法找回。

实际：云盘回收站中的文件可保留30天，期间可自助恢复；超过30天但未满35天的，可联系支持团队通过索引备份定位恢复（属付费服务）；超过35天后无法恢复。

引用：星桥云盘产品功能手册.md, 星桥云盘数据备份与保留策略.md

人工结论：待复核

### PD-03 我们是基础版，星桥云盘的存储额度到底是多少？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥云盘套餐与配额对照表.md

检索来源：星桥云盘套餐与配额对照表.md, 星桥云盘套餐与配额对照表.md, 星桥云盘产品功能手册.md, 星桥会议常见问题 FAQ.md, 星桥会议套餐配额与并发说明.md

参考：基础版存储配额 100 GB，标准版 1 TB，旗舰版 5 TB；回收站与历史版本同样计入实际占用。

实际：基础版的星桥云盘存储额度是100 GB。

引用：星桥云盘套餐与配额对照表.md, 星桥云盘产品功能手册.md

人工结论：待复核

### PD-04 用基础版开一场会议，最长能开多久？

难度：easy ｜ 库：product ｜ split：test

标注来源：星桥会议套餐配额与并发说明.md

检索来源：星桥会议常见问题 FAQ.md, 星桥会议常见问题 FAQ.md, 星桥会议套餐配额与并发说明.md, 星桥会议接口接入与鉴权指南.md, 星桥科技统一账号与单点登录说明.md

参考：基础版单场时长上限 40 分钟，达到上限会议自动结束，可立即重新发起；标准版与旗舰版单场最长 24 小时。

实际：用基础版开一场会议，最长能开40分钟。

引用：星桥会议常见问题 FAQ.md, 星桥会议常见问题 FAQ.md, 星桥会议套餐配额与并发说明.md, 星桥会议接口接入与鉴权指南.md

人工结论：待复核

### PD-05 工单里最多能挂多大的附件？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥工单产品功能手册.md

检索来源：星桥工单产品功能手册.md, 星桥工单产品功能手册.md, 星桥工单常见问题 FAQ.md, 星桥工单版本发布说明 v4.2.md, 星桥工单常见故障排查.md

参考：单个附件不超过 50 MB，单工单累计不超过 200 MB，超过会提示改用云盘链接。

实际：工单里单个附件最大为50 MB，单工单累计附件总大小上限为200 MB。

引用：星桥工单产品功能手册.md, 星桥工单常见问题 FAQ.md, 星桥工单常见故障排查.md

人工结论：待复核

### PD-06 调用星桥会议接口拿到的令牌能用多长时间？

难度：easy ｜ 库：product ｜ split：test

标注来源：星桥会议接口接入与鉴权指南.md

检索来源：星桥会议接口接入与鉴权指南.md, 星桥科技统一账号与单点登录说明.md, 星桥工单接口鉴权与调用规范.md, 星桥科技统一账号与单点登录说明.md, 星桥科技统一账号与单点登录说明.md

参考：会议接口访问令牌有效期 24 小时，且不支持刷新令牌，过期后需要重新换取。

实际：调用星桥会议接口拿到的令牌有效期为24小时，不支持刷新，过期后需重新调用`POST /api/v2/auth/token`换取新令牌。

引用：星桥会议接口接入与鉴权指南.md, 星桥科技统一账号与单点登录说明.md, 星桥科技统一账号与单点登录说明.md

人工结论：待复核

### PD-07 星桥云盘开放接口的访问令牌有效期是几个小时？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥云盘开放接口接入指南.md

检索来源：星桥科技统一账号与单点登录说明.md, 星桥会议接口接入与鉴权指南.md, 星桥云盘开放接口接入指南.md, 星桥工单接口鉴权与调用规范.md, 星桥云盘账号与共享授权说明.md

参考：云盘访问令牌有效期 2 小时，刷新令牌有效期 30 天，且刷新令牌只能使用一次。

实际：星桥云盘开放接口的访问令牌有效期是2小时。

引用：星桥科技统一账号与单点登录说明.md, 星桥云盘开放接口接入指南.md, 星桥云盘账号与共享授权说明.md

人工结论：待复核

### PD-08 星桥工单的接口令牌多久会过期？

难度：easy ｜ 库：product ｜ split：dev

标注来源：星桥工单接口鉴权与调用规范.md

检索来源：星桥工单接口鉴权与调用规范.md, 星桥会议接口接入与鉴权指南.md, 星桥工单 4.x 迁移说明.md, 星桥科技统一账号与单点登录说明.md, 星桥科技统一账号与单点登录说明.md

参考：工单接口访问令牌有效期 1 小时，刷新令牌有效期 14 天。

实际：星桥工单的接口访问令牌有效期为1小时。

引用：星桥工单接口鉴权与调用规范.md, 星桥工单 4.x 迁移说明.md, 星桥科技统一账号与单点登录说明.md, 星桥科技统一账号与单点登录说明.md

人工结论：待复核

### PD-09 我们的上传脚本还在用老接口，官方说该换成哪个新接口了？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥云盘开放接口接入指南.md

检索来源：星桥会议 1.x 客户端停用公告.md, 星桥云盘开放接口接入指南.md, 星桥云盘开放接口接入指南.md, 星桥会议版本发布说明 v2.8.md, 星桥会议 1.x 客户端停用公告.md

参考：旧上传接口 POST /api/v2/files/upload 自 v3.0 起废弃，请改用 POST /api/v3/drive/objects；旧接口计划在 v3.6 停止服务。

实际：官方要求将上传脚本的接口从 `room.create` 迁移到 `rooms.create`。

引用：星桥会议 1.x 客户端停用公告.md, 星桥会议版本发布说明 v2.8.md, 星桥会议 1.x 客户端停用公告.md

人工结论：待复核

### PD-10 会议接口里的 room.create 还能继续用吗，应该换成什么？

难度：paraphrase ｜ 库：product ｜ split：test

标注来源：星桥会议接口接入与鉴权指南.md

检索来源：星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议版本发布说明 v2.8.md, 星桥会议接口接入与鉴权指南.md, 星桥会议接口接入与鉴权指南.md

参考：旧接口 room.create 自 v2.5 起废弃，请改用 rooms.create，REST 路径为 POST /api/v2/rooms。

实际：会议接口里的 room.create 已自 v2.5 起废弃，当前仍可调用但不推荐继续使用；应迁移到 rooms.create（REST 路径为 POST /api/v2/rooms）。该接口支持参会人权限字段，且返回结构符合 v2 规范。旧接口计划于 2026-10-31 停止服务。

引用：星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议接口接入与鉴权指南.md

人工结论：待复核

### PD-11 我们的集成里还在用 X-Legacy-Token 这个请求头，现在有替代做法吗？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥工单接口鉴权与调用规范.md

检索来源：星桥科技 API 通用错误码与重试规范.md, 星桥工单错误码与限流对照表.md, 星桥会议 1.x 客户端停用公告.md, 星桥工单 4.x 迁移说明.md, 星桥工单 4.x 迁移说明.md

参考：旧鉴权请求头 X-Legacy-Token 自 v4.1 起废弃，请改用标准 Bearer 令牌，且旧请求头不支持细粒度权限范围。

实际：是的，X-Legacy-Token 已自 v4.1 起废弃，应改用标准的 Bearer 令牌鉴权方式，即在请求头中使用 `Authorization: Bearer <token>`。

引用：星桥工单 4.x 迁移说明.md

人工结论：待复核

### PD-12 客户端同步协议是不是换过了，旧协议还能不能用？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥云盘开放接口接入指南.md

检索来源：星桥云盘客户端兼容性矩阵.md, 星桥工单 4.x 迁移说明.md, 星桥云盘同步失败排查手册.md, 星桥会议 1.x 客户端停用公告.md, 星桥云盘套餐与配额对照表.md

参考：旧同步协议 sync-legacy 自 v3.2 起废弃，请改用 sync-v3，旧协议不再修复缺陷，冲突时只能后写覆盖。

实际：是的，客户端同步协议已更换为 `sync-v3`；旧协议 `sync-legacy` 仍可使用（服务端 3.4 同时支持），但已被废弃，缺陷不再修复，且自 v3.2 起已废弃，客户端重启后会自动切换。建议尽快迁移，因长期未重启的终端可能仍在使用旧协议导致同步异常。

引用：星桥云盘客户端兼容性矩阵.md, 星桥云盘同步失败排查手册.md

人工结论：待复核

### PD-13 公司里几台老会议客户端一直提示版本过低登不上，是怎么回事？

难度：paraphrase ｜ 库：product ｜ split：test

标注来源：星桥会议 1.x 客户端停用公告.md

检索来源：星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议版本发布说明 v2.8.md

参考：星桥会议 1.x 桌面客户端自 v2.0 起已停用，请改用 2.x 客户端；过渡期已于 2026-07-19 结束，之后无法登录。

实际：因为公司使用的星桥会议1.x老版本客户端已停用，自2026-07-19过渡期结束后，服务端将直接拒绝1.x客户端的登录请求，提示“版本过低，请升级后使用”。这是既定版本策略，非临时故障。老旧会议客户端无法登录的根本原因是1.x编解码协商机制与新版本不兼容，且存在约8%单向音频问题，该问题无法在1.x侧修复。

引用：星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议 1.x 客户端停用公告.md

人工结论：待复核

### PD-14 工单邮件通知显示发送成功，但同事说收不到，通常卡在哪里？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥工单通知模板与回调配置.md

检索来源：星桥工单常见故障排查.md, 星桥工单常见故障排查.md, 星桥工单常见问题 FAQ.md, 星桥工单常见问题 FAQ.md, 星桥工单常见故障排查.md

参考：常见原因是企业防火墙只放通了 25 端口，邮件通道使用 2525 端口，未放通就会出现发送状态成功但用户收不到的假象。

实际：通常卡在邮件发信中继的2525端口未被企业防火墙放通，或收件方企业邮箱将发信域名拦截。此外还需检查：通知规则是否启用、模板变量是否缺失导致渲染失败、发送日志状态是否为`bounced`（表示退信）。

引用：星桥工单常见故障排查.md, 星桥工单常见故障排查.md, 星桥工单常见问题 FAQ.md, 星桥工单常见问题 FAQ.md, 星桥工单常见故障排查.md

人工结论：待复核

### PD-15 新入职的同事点提交工单没反应，一般是什么原因？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥工单常见问题 FAQ.md

检索来源：星桥工单常见问题 FAQ.md, 星桥工单常见故障排查.md, 星桥工单常见故障排查.md, 星桥工单提交与升级机制.md, 星桥工单 SLA 分级与响应时限.md

参考：常见原因有两个：账号未加入服务范围，或账号角色仅具备查看权限，需管理员在成员与服务范围中确认。

实际：新入职同事提交工单没反应，常见原因有两个：一是账号未加入服务范围（需管理员在控制台"组织—服务范围"中配置），二是账号角色仅具备查看权限、缺少提交权限（需管理员在"成员—角色"中确认并调整）。此外，若使用浏览器提交，还可能是广告拦截插件误拦截了含'ticket'关键字的请求。

引用：星桥工单常见问题 FAQ.md, 星桥工单常见故障排查.md

人工结论：待复核

### PD-16 怎么判断会议卡顿是网络问题还是产品本身的问题？

难度：paraphrase ｜ 库：product ｜ split：test

标注来源：星桥会议音视频质量排查指南.md

检索来源：星桥会议音视频质量排查指南.md, 星桥会议音视频质量排查指南.md, 星桥会议错误码速查表.md, 星桥会议音视频质量排查指南.md, 星桥会议错误码速查表.md

参考：先看网络诊断四项：丢包率低于 5%、抖动低于 30 毫秒、时延低于 200 毫秒、上行不低于 1.5 Mbps；四项合格仍卡顿再排查客户端性能。

实际：判断会议卡顿是网络问题还是产品本身问题，需按以下步骤量化排查：

1. **先做网络诊断**：让用户在会议中打开"设置—网络诊断"，检查四项指标：
   - 丢包率 ≥5% → 网络问题（典型表现：声音断续、画面马赛克）
   - 网络抖动 ≥30ms → 网络问题（典型表现：声音忽快忽慢）
   - 往返时延 ≥200ms → 网络问题（典型表现：对话明显停顿）
   - 上行带宽 <1.5 Mbps（720p需求）→ 网络问题（导致自己画面被降质）
   → 若任一指标不合格，优先处理网络（如切换网络、关闭下载、改用有线）。

2. **若四项全部合格但仍卡顿**，则排除纯网络问题，进入后续排查：
   - 检查防火墙是否放通 UDP 50000–50100（媒体端口）和 TCP 443/8443（信令端口），未放通会导致"能进会议但无音视频"（故障码 M101）；
   - 验证是否为设备问题（如麦克风权限、摄像头被独占、输出设备选错）；
   - 检查客户端版本是否低于2.0（已停用）或存在编解码协商失败（M105）；
   - 若多个不同租户同一时段卡顿，且控制台显示某区域丢包分档整体下滑持续超30分钟，则可能为服务端媒体节点问题；
   - 注意：`ROOM_LICENSE_EXHAUSTED`（429）仅导致"发起会议失败"，不引起卡顿，勿混淆。

引用：星桥会议音视频质量排查指南.md, 星桥会议音视频质量排查指南.md

人工结论：待复核

### PD-17 云盘客户端图标变成黄色感叹号，是不是文件全丢了？

难度：paraphrase ｜ 库：product ｜ split：dev

标注来源：星桥云盘同步失败排查手册.md

检索来源：星桥云盘同步失败排查手册.md, 星桥会议录制与存储保留策略.md, 星桥云盘产品功能手册.md, 星桥工单接口鉴权与调用规范.md, 星桥会议录制与存储保留策略.md

参考：黄色感叹号表示部分失败，不是全部丢失；应在客户端最近错误中查看错误码再决定处理动作。

实际：不是。黄色感叹号表示部分同步失败，而非文件全部丢失。根据排查手册，该图标含义是'部分失败'，需查看'最近错误'中的具体错误码来定位原因，例如并发超限、上传超时或配额不足等。

引用：星桥云盘同步失败排查手册.md

人工结论：待复核

### PD-18 会议录制到底保留多久，是 90 天还是 30 天？

难度：paraphrase ｜ 库：product ｜ split：test

标注来源：星桥会议录制与存储保留策略.md

检索来源：星桥会议录制与存储保留策略.md, 星桥会议录制与存储保留策略.md, 星桥云盘数据备份与保留策略.md, 星桥会议录制与存储保留策略.md, 星桥会议与云盘集成说明.md

参考：两段叠加：标准版会议侧保留 90 天，到期移入云盘回收站再保留 30 天，从生成到彻底不可恢复最长约 120 天；旗舰版为 180 加 30 等于 210 天。

实际：会议录制的默认保留期是90天（标准版）或180天（旗舰版），但可调整的最短保留期为30天。因此，既不是固定90天也不是固定30天，而是根据套餐和配置决定：标准版默认90天，最低可设为30天；旗舰版默认180天，最低也可设为30天。

引用：星桥会议录制与存储保留策略.md, 星桥会议录制与存储保留策略.md

人工结论：待复核

### PD-19 云盘接口报 429 说并发超限，具体上限是几个？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥云盘错误码说明.md

检索来源：星桥云盘错误码说明.md, 星桥工单错误码与限流对照表.md, 星桥工单错误码与限流对照表.md, 星桥科技 API 通用错误码与重试规范.md, 星桥科技 API 通用错误码与重试规范.md

参考：星桥云盘的 429 只有一种成因：并发上传数超过 8 个，错误码为 UPLOAD_CONCURRENCY_EXCEEDED，应降低并发并按 1 秒、2 秒、4 秒退避重试。

实际：云盘接口报 429 并发超限的具体上限是同一应用同时上传超过 8 个分片或 8 个会话。

引用：星桥云盘错误码说明.md

人工结论：待复核

### PD-20 工单接口每分钟最多能调用多少次，超了会怎样？

难度：numeric ｜ 库：product ｜ split：test

标注来源：星桥工单错误码与限流对照表.md

检索来源：星桥工单接口鉴权与调用规范.md, 星桥工单常见故障排查.md, 星桥工单错误码与限流对照表.md, 星桥工单常见故障排查.md, 星桥工单产品功能手册.md

参考：工单接口限流为每令牌每分钟 120 次，采用 60 秒滑动窗口，超出返回 429 并在响应头给出 Retry-After。

实际：工单接口每分钟最多能调用120次（读取类）或60次（写入类），均按每令牌每分钟计算，采用60秒滑动窗口。超出后返回HTTP 429状态码，响应体code为RATE_LIMITED，并在响应头中返回Retry-After（单位为秒），需按该值等待后重试。批量接口按条目数计费频次（如单次提交20条消耗20次额度），异步导入作业接口则按作业次数计费。

引用：星桥工单接口鉴权与调用规范.md, 星桥工单错误码与限流对照表.md

人工结论：待复核

### PD-21 开会时提示会议室资源繁忙，对应的是哪个错误码？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥会议错误码速查表.md

检索来源：星桥会议错误码速查表.md, 星桥会议错误码速查表.md, 星桥会议错误码速查表.md, 星桥会议接口接入与鉴权指南.md, 星桥会议套餐配额与并发说明.md

参考：错误码为 ROOM_LICENSE_EXHAUSTED，含义是并发会议室许可已满，应结束闲置会议或申请临时扩容。

实际：4002

引用：星桥会议错误码速查表.md, 星桥会议错误码速查表.md

人工结论：待复核

### PD-22 星桥统一网关的总量限流阈值是多少，超了返回什么？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥科技 API 通用错误码与重试规范.md

检索来源：星桥科技 API 通用错误码与重试规范.md, 星桥工单错误码与限流对照表.md, 星桥云盘错误码说明.md, 星桥工单错误码与限流对照表.md, 星桥会议版本发布说明 v2.8.md

参考：网关按租户维度限流，阈值为每分钟 6000 次，超出返回 429 GATEWAY_RATE_LIMITED，并给出 X-XQ-Rate-Limit-Reset 响应头。

实际：星桥统一网关的总量限流阈值是每租户每分钟6000次，超出时返回HTTP状态码429及错误码`GATEWAY_RATE_LIMITED`。

引用：星桥科技 API 通用错误码与重试规范.md, 星桥工单错误码与限流对照表.md

人工结论：待复核

### PD-23 我们忘了续费，多久之内补上钱数据不会被清理？

难度：numeric ｜ 库：product ｜ split：test

标注来源：星桥科技统一计费与续费口径说明.md

检索来源：星桥科技统一计费与续费口径说明.md, 星桥云盘套餐与配额对照表.md, 星桥会议录制与存储保留策略.md, 星桥云盘套餐与配额对照表.md, 星桥科技统一计费与续费口径说明.md

参考：续费到期后有 15 天宽限期，服务只读；宽限期后进入 90 天冻结期，冻结结束才进入数据清理流程，从到期到彻底清理约 105 天。

实际：在宽限期（到期后15天内）补上费用，数据不会被清理，续费后服务立即恢复；若超过15天进入冻结期（最长90天），数据仍保留，结清欠费即可恢复；但若冻结满90天（即到期后共105天）进入清理期，则数据将被按流程清理，无法恢复。

引用：星桥科技统一计费与续费口径说明.md, 星桥云盘套餐与配额对照表.md, 星桥科技统一计费与续费口径说明.md

人工结论：待复核

### PD-24 会议室网络需要放通哪些 UDP 端口？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥会议音视频质量排查指南.md

检索来源：星桥会议版本发布说明 v2.8.md, 星桥会议音视频质量排查指南.md, 星桥会议常见问题 FAQ.md, 星桥会议产品功能手册.md, 星桥会议产品功能手册.md

参考：媒体流使用 UDP 50000 至 50100，信令走 TCP 443；会议室连接器还需要放通 TCP 8443。

实际：会议室网络需要放通 UDP 50000 至 50100 端口。

引用：星桥会议版本发布说明 v2.8.md, 星桥会议常见问题 FAQ.md, 星桥会议产品功能手册.md

人工结论：待复核

### PD-25 一线支持多久没给出方向就要把工单升级到二线？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥工单提交与升级机制.md

检索来源：星桥工单提交与升级机制.md, 星桥工单提交与升级机制.md, 星桥工单提交与升级机制.md, 星桥工单常见问题 FAQ.md, 星桥工单提交与升级机制.md

参考：一线在受理后 10 分钟内完成首次分类，30 分钟内无法给出明确方向应升级二线；二线 2 小时未定位根因且属 P0/P1 时升级三线。

实际：一线支持在30分钟内未给出明确方向，应将工单升级到二线。

引用：星桥工单提交与升级机制.md, 星桥工单提交与升级机制.md, 星桥工单提交与升级机制.md

人工结论：待复核

### PD-26 云盘的 Webhook 投递失败会重试几次，间隔怎么排？

难度：numeric ｜ 库：product ｜ split：test

标注来源：星桥云盘 Webhook 事件回调说明.md

检索来源：星桥工单通知模板与回调配置.md, 星桥云盘 Webhook 事件回调说明.md, 星桥云盘 Webhook 事件回调说明.md, 星桥云盘同步失败排查手册.md, 星桥科技 API 通用错误码与重试规范.md

参考：投递失败共重试 5 次，间隔为 10 秒、30 秒、90 秒、270 秒、810 秒，总跨度约 20 分钟；全部失败后可在 7 天内手工重放。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-27 调用云盘开放接口时，连接超时和读超时建议设多少秒？

难度：numeric ｜ 库：product ｜ split：dev

标注来源：星桥云盘开放接口接入指南.md

检索来源：星桥工单 SLA 分级与响应时限.md, 星桥云盘数据导入导出操作指南.md, 星桥工单接口鉴权与调用规范.md, 星桥科技 API 通用错误码与重试规范.md, 星桥云盘错误码说明.md

参考：连接超时建议 5 秒，读超时 30 秒（分片上传可放宽到 60 秒），重试 3 次，退避 1 秒、2 秒、4 秒。

实际：连接超时建议设为5秒，读超时建议设为30秒。

引用：星桥科技 API 通用错误码与重试规范.md

人工结论：待复核

### PD-28 会议客户端多久没有心跳就会被判定掉线？

难度：numeric ｜ 库：product ｜ split：test

标注来源：星桥会议音视频质量排查指南.md

检索来源：星桥会议产品功能手册.md, 星桥会议音视频质量排查指南.md, 星桥会议 1.x 客户端停用公告.md, 星桥会议错误码速查表.md, 星桥会议接口接入与鉴权指南.md

参考：心跳间隔为 5 秒，连续 3 次无响应即 15 秒判定掉线。

实际：会议客户端连续3次心跳无响应（共15秒）会被判定掉线。

引用：星桥会议产品功能手册.md

人工结论：待复核

### PD-29 我们想把云盘从 2.9 升到 3.x，起点版本要求和老客户端兼容情况怎么样？

难度：multi_source ｜ 库：product ｜ split：dev

标注来源：星桥云盘 3.x 升级说明.md, 星桥云盘客户端兼容性矩阵.md

检索来源：星桥云盘客户端兼容性矩阵.md, 星桥云盘 3.x 升级说明.md, 星桥云盘 2.x 升级说明.md, 星桥会议 1.x 客户端停用公告.md, 星桥云盘客户端兼容性矩阵.md

参考：3.x 升级要求先升到 2.9.7，服务端内存至少 16 GB、停机 90 分钟且不可回滚；客户端方面，2.9 及以下在 3.0 至 3.2 为只读，3.3.x 起拒绝登录，必须使用 3.0 及以上客户端。

实际：起点版本要求必须为 2.9.7；老客户端兼容情况：2.9 版本客户端在服务端升级至 3.0–3.2 时支持只读（浏览、下载、预览），3.3.x 起仅支持只读（第15天起拒绝登录）；2.4–2.8 版本客户端在 3.0–3.2 服务端仅支持只读，3.3.x 及以上拒绝登录。3.0 及以上客户端完全兼容 3.x 服务端。

引用：星桥云盘客户端兼容性矩阵.md, 星桥云盘 3.x 升级说明.md

人工结论：待复核

### PD-30 会议发起失败报了 429，处理方式和普通限流一样吗？

难度：multi_source ｜ 库：product ｜ split：dev

标注来源：星桥会议错误码速查表.md, 星桥科技 API 通用错误码与重试规范.md

检索来源：星桥会议错误码速查表.md, 星桥工单错误码与限流对照表.md, 星桥会议常见问题 FAQ.md, 星桥云盘错误码说明.md, 星桥云盘错误码说明.md

参考：会议 429 有两种：RATE_LIMITED 是每令牌每分钟 300 次调用频率超限，可退避重试；ROOM_LICENSE_EXHAUSTED 是并发会议室许可已满，需结束闲置会议或扩容。而 GATEWAY_RATE_LIMITED 属于统一网关的租户总量限流，三者不可套用同一处理方式。

实际：不一样。会议发起失败报429需先根据code区分成因：若code为RATE_LIMITED（4001），属调用频率超限，应退避重试（2秒、4秒、8秒）；若code为ROOM_LICENSE_EXHAUSTED（4002），属并发会议室许可已满，需结束闲置会议或申请临时扩容，而非等待重试。将4002误判为普通限流会导致会议持续无法发起。

引用：星桥会议错误码速查表.md, 星桥会议常见问题 FAQ.md, 星桥云盘错误码说明.md

人工结论：待复核

### PD-31 批量上传脚本偶发失败，是不是和并发数设置有关？

难度：multi_source ｜ 库：product ｜ split：test

标注来源：星桥云盘错误码说明.md, 星桥云盘同步失败排查手册.md

检索来源：星桥云盘数据导入导出操作指南.md, 星桥云盘错误码说明.md, 星桥工单常见故障排查.md, 星桥云盘数据导入导出操作指南.md, 星桥云盘错误码说明.md

参考：并发上传数超过 8 个会返回 429 UPLOAD_CONCURRENCY_EXCEEDED；处理办法是关闭部分上传任务，或把 drive.upload.parallel 调整为 4。

实际：是的，批量上传脚本偶发失败可能与并发数设置有关。资料明确指出：当并发上传数超过8个时，服务端会拒绝请求并返回429错误（错误码 UPLOAD_CONCURRENCY_EXCEEDED）；且该429仅由并发超限导致，与请求频率无关。建议将 --parallel 参数设为8以下，并确保未关闭的上传会话已正确释放。

引用：星桥云盘数据导入导出操作指南.md, 星桥云盘错误码说明.md, 星桥云盘数据导入导出操作指南.md, 星桥云盘错误码说明.md

人工结论：待复核

### PD-32 工单通知收不到时，要同时检查哪两处配置？

难度：multi_source ｜ 库：product ｜ split：dev

标注来源：星桥工单通知模板与回调配置.md, 星桥工单常见故障排查.md

检索来源：星桥工单常见故障排查.md, 星桥工单常见故障排查.md, 星桥工单常见问题 FAQ.md, 星桥工单通知模板与回调配置.md, 星桥工单常见问题 FAQ.md

参考：一是邮件通道的 2525 端口是否放通（工单常见故障排查中给出该端口），二是 Webhook 回调的失败重试策略，回调失败重试 4 次。

实际：要同时检查通知规则是否启用和模板变量是否为空。

引用：星桥工单常见故障排查.md, 星桥工单常见问题 FAQ.md, 星桥工单常见问题 FAQ.md

人工结论：待复核

### PD-33 会议录制文件占用谁的存储配额，容量该怎么估？

难度：multi_source ｜ 库：product ｜ split：test

标注来源：星桥会议录制与存储保留策略.md, 星桥会议与云盘集成说明.md

检索来源：星桥会议录制与存储保留策略.md, 星桥会议与云盘集成说明.md, 星桥会议与云盘集成说明.md, 星桥会议套餐配额与并发说明.md, 星桥云盘产品功能手册.md

参考：录制文件计入云盘存储配额，存放在云盘存储配额对应的会议录制空间；1 小时 720p 录制约占 450 MB，1080p 约 900 MB。

实际：会议录制文件占用云盘存储配额。容量估算方法：一场1小时的720p会议录制约占450 MB，1080p约900 MB；例如每日20场1小时会议全部录制，720p下月增约270 GB。

引用：星桥会议录制与存储保留策略.md, 星桥会议与云盘集成说明.md, 星桥会议与云盘集成说明.md, 星桥会议套餐配额与并发说明.md

人工结论：待复核

### PD-34 P0 工单首次响应到底按 15 分钟还是 30 分钟算？

难度：multi_source ｜ 库：product ｜ split：dev

标注来源：星桥工单 SLA 分级与响应时限.md, 星桥科技服务等级协议 SLA 总则.md

检索来源：星桥工单 SLA 分级与响应时限.md, 星桥科技服务等级协议 SLA 总则.md, 星桥科技服务等级协议 SLA 总则.md, 星桥工单提交与升级机制.md, 星桥科技服务等级协议 SLA 总则.md

参考：工单产品专章的 P0 首次响应为 15 分钟；公司总则的 30 分钟是兜底条款，两者存在差异时以产品专章为准，对客户按 15 分钟承诺。

实际：P0 工单首次响应按 15 分钟算。根据工单产品专章，P0 首次响应时限为 15 分钟，优于公司 SLA 总则的 30 分钟兜底条款；产品专章优先适用，客服向客户承诺时必须引用 15 分钟，引用 30 分钟属于服务事故。

引用：星桥工单 SLA 分级与响应时限.md, 星桥科技服务等级协议 SLA 总则.md, 星桥科技服务等级协议 SLA 总则.md, 星桥科技服务等级协议 SLA 总则.md

人工结论：待复核

### PD-35 星桥云盘移动端有没有图片文字识别功能，能直接提取发票文字吗？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议与云盘集成说明.md, 星桥云盘产品功能手册.md, 星桥云盘产品功能手册.md, 星桥会议版本发布说明 v2.8.md, 星桥科技统一计费与续费口径说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-36 星桥工单能不能直接对接外部客户关系管理系统的原生连接器？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单与云盘集成配置说明.md, 星桥工单提交与升级机制.md, 星桥云盘产品功能手册.md, 星桥工单常见问题 FAQ.md, 星桥工单产品功能手册.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-37 星桥会议的端到端加密具体是怎么实现的，密钥由谁托管？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议与云盘集成说明.md, 星桥会议产品功能手册.md, 星桥会议录制与存储保留策略.md, 星桥会议常见问题 FAQ.md, 星桥会议预约与日历集成说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-38 星桥科技的安全审计报告是哪家机构出的，报告编号是多少？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥科技 API 通用错误码与重试规范.md, 星桥会议错误码速查表.md, 星桥科技统一账号与单点登录说明.md, 星桥工单错误码与限流对照表.md, 星桥云盘错误码说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-39 星桥云盘私有化部署通过了哪些国产化操作系统的认证？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘客户端兼容性矩阵.md, 星桥云盘版本发布说明 v3.4.md, 星桥云盘产品功能手册.md, 星桥云盘账号与共享授权说明.md, 星桥云盘版本发布说明 v3.4.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-40 星桥工单每个坐席一年的具体报价是多少钱？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议套餐配额与并发说明.md, 星桥科技统一计费与续费口径说明.md, 星桥工单通知模板与回调配置.md, 星桥工单提交与升级机制.md, 星桥会议套餐配额与并发说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-41 星桥会议的语音转写一共支持多少种语言，有小语种模型吗？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议版本发布说明 v2.8.md, 星桥会议产品功能手册.md, 星桥会议版本发布说明 v2.8.md, 星桥会议套餐配额与并发说明.md, 星桥会议与云盘集成说明.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-42 星桥云盘移动端支持分屏拖拽整理文件夹吗？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘产品功能手册.md, 星桥会议与云盘集成说明.md, 星桥云盘产品功能手册.md, 星桥云盘版本发布说明 v3.4.md, 星桥云盘数据备份与保留策略.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-43 星桥科技的数据中心一共在哪些城市，具体地址是什么？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘产品功能手册.md, 星桥会议套餐配额与并发说明.md, 星桥云盘数据备份与保留策略.md, 星桥工单提交与升级机制.md, 星桥云盘版本发布说明 v3.4.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-44 星桥工单支持填报工时并导出工时表吗？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单提交与升级机制.md, 星桥工单 SLA 分级与响应时限.md, 星桥工单通知模板与回调配置.md, 星桥工单常见问题 FAQ.md, 星桥工单产品功能手册.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-45 星桥云盘的 Webhook 签名用的是哪种哈希算法，密钥长度是多少位？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘 Webhook 事件回调说明.md, 星桥云盘开放接口接入指南.md, 星桥科技统一账号与单点登录说明.md, 星桥云盘版本发布说明 v3.4.md, 星桥工单通知模板与回调配置.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-46 会议录制文件的视频码率具体是多少 kbps？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议录制与存储保留策略.md, 星桥会议产品功能手册.md, 星桥会议产品功能手册.md, 星桥会议与云盘集成说明.md, 星桥会议音视频质量排查指南.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-47 工单满意度调查问卷一共有几道题，题目内容是什么？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单产品功能手册.md, 星桥工单产品功能手册.md, 星桥工单产品功能手册.md, 星桥工单常见问题 FAQ.md, 星桥科技服务等级协议 SLA 总则.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-48 星桥云盘 3.4.2 修复的安全问题对应哪个漏洞编号？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥云盘错误码说明.md, 星桥科技 API 通用错误码与重试规范.md, 星桥云盘版本发布说明 v3.4.md, 星桥云盘同步失败排查手册.md, 星桥工单错误码与限流对照表.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-49 一台星桥会议连接器最多能同时承载几路会议？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥会议套餐配额与并发说明.md, 星桥会议版本发布说明 v2.8.md, 星桥会议套餐配额与并发说明.md, 星桥会议产品功能手册.md, 星桥会议产品功能手册.md

参考：（无）

实际：一台星桥会议连接器建议最多管理5间会议室。

引用：星桥会议产品功能手册.md

人工结论：待复核

### PD-50 星桥工单自动分派里，技能组加权轮询的权重计算公式是什么？

难度：refusal ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：星桥工单自动分派规则说明.md, 星桥工单自动分派规则说明.md, 星桥工单自动分派规则说明.md, 星桥工单错误码与限流对照表.md, 星桥工单产品功能手册.md

参考：（无）

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-51 星桥云盘的回收站保留多少天，过期后还能恢复吗？

难度：cross_kb ｜ 库：product ｜ split：dev

标注来源：（期望拒答）

检索来源：正版软件授权与 License 台账.md, 权限申请与最小权限矩阵.md, 终端设备领用与归还登记表.md, 共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md

参考：答案只存在于产品知识库：星桥云盘回收站保留期为 30 天，超过后进入清理队列无法自助恢复。该问题在 IT 知识库中没有对应资料，跨库提问应当拒答。

实际：星桥云盘的回收站保留30天，过期后无法自助恢复，需提交文件误删恢复申请工单，由服务台或系统与账号组从备份副本中尝试恢复。

引用：共享盘目录结构与权限规范.md, 文件误删恢复申请指引.md

人工结论：待复核

### PD-52 星桥工单 P0 事件的首次响应时限是多少分钟？

难度：cross_kb ｜ 库：product ｜ split：dev

标注来源：（期望拒答）

检索来源：统一身份认证（SSO）接入规范.md, 信息安全事件分级与上报流程.md, 信息安全事件分级与上报流程.md, 权限申请与最小权限矩阵.md, VPN 客户端故障排查清单.md

参考：答案只存在于产品知识库：星桥工单 P0 首次响应为 15 分钟、恢复 4 小时。该问题在 IT 知识库中无对应资料，跨库提问应当拒答。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-53 星桥会议接口的访问令牌有效期是多久，支持刷新吗？

难度：cross_kb ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：无线网络接入与访客 Wi-Fi 管理办法.md, 权限申请与最小权限矩阵.md, 无线网络接入与访客 Wi-Fi 管理办法.md, AD 域账号与权限管理规定.md, 正版软件授权与 License 台账.md

参考：答案只存在于产品知识库：星桥会议接口访问令牌有效期 24 小时且不支持刷新令牌。该问题在 IT 知识库中无对应资料，跨库提问应当拒答。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-54 星桥云盘基础版套餐的存储配额是多少 GB？

难度：cross_kb ｜ 库：product ｜ split：dev

标注来源：（期望拒答）

检索来源：职级体系与薪资带宽表.md, 信息安全与数据保密规范.md, 请假类型与假期额度对照表.md, 关于调整 2026 年度差旅住宿标准的通知.md, 合规红线与行为准则.md

参考：答案只存在于产品知识库：星桥云盘基础版存储配额为 100 GB，标准版 1 TB。该问题在人力资源知识库中无对应资料，跨库提问应当拒答。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-55 星桥工单里单个附件的大小上限是多少兆？

难度：cross_kb ｜ 库：product ｜ split：test

标注来源：（期望拒答）

检索来源：采购与付款审批权限表.md, 费用报销审批权限表.md, 合规红线与行为准则.md, 信息安全与数据保密规范.md, 用章与合同审批权限表.md

参考：答案只存在于产品知识库：星桥工单单个附件不超过 50 MB，单工单累计不超过 200 MB。该问题在人力资源知识库中无对应资料，跨库提问应当拒答。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核

### PD-56 星桥会议媒体流使用的 UDP 端口范围是多少？

难度：cross_kb ｜ 库：product ｜ split：dev

标注来源：（期望拒答）

检索来源：职级体系与薪资带宽表.md, 信息安全与数据保密规范.md, 合规红线与行为准则.md, 采购与付款审批权限表.md, 培训管理办法.md

参考：答案只存在于产品知识库：星桥会议媒体流使用 UDP 50000 至 50100，信令走 TCP 443。该问题在人力资源知识库中无对应资料，跨库提问应拒答。

实际：现有知识库资料不足，无法回答这个问题。

引用：无

人工结论：待复核
