# KnowOps 星桥科技合成数据集评估

**重要声明**：本数据集全部为合成内容（虚构企业「星桥科技」），不对应任何真实企业制度、产品或人员。指标只代表在该合成语料上的表现，**不能**作为真实企业准确率或生产性能依据。

- 运行标识：synthetic-v1
- 题数：31（31 有答案 / 0 期望拒答）
- 知识库：it=评估-synthetic-v1-IT 支持, hr=评估-synthetic-v1-人事制度, product=评估-synthetic-v1-产品与客服
- 证据覆盖：分别在各标注来源的切片中匹配该来源的 terms；允许跨切片联合覆盖。
- Recall@1 仅检查第一条；MRR 检查首个支持证据；nDCG 按不同来源去重，理想值包含未召回来源。
- 隔离题单列，计入期望拒答题；无泄漏与正确拒答是两个不同指标。

## 自动指标

```json
{
  "questions": 31,
  "successful_requests": 31,
  "answerable_questions": 31,
  "refusal_questions": 0,
  "isolation_questions": 0,
  "isolation_leakage_rate": null,
  "evidence_complete_at_k": 0.6452,
  "source_recall_at_k": 0.9032,
  "chunk_recall_at_1": 0.1935,
  "chunk_recall_at_k": 0.6452,
  "mrr_at_k": 0.4677,
  "ndcg_at_k": 0.5233,
  "timings_ms": {
    "retrieval": {
      "p50": 390.49,
      "p95": 404.35
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
  "easy": {
    "questions": 8,
    "successful_requests": 8,
    "answerable_questions": 8,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.875,
    "source_recall_at_k": 1.0,
    "chunk_recall_at_1": 0.125,
    "chunk_recall_at_k": 0.875,
    "mrr_at_k": 0.5208,
    "ndcg_at_k": 0.6116,
    "timings_ms": {
      "retrieval": {
        "p50": 326.89,
        "p95": 18505.71
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "multi_source": {
    "questions": 3,
    "successful_requests": 3,
    "answerable_questions": 3,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.0,
    "source_recall_at_k": 0.3333,
    "chunk_recall_at_1": 0.0,
    "chunk_recall_at_k": 0.0,
    "mrr_at_k": 0.1111,
    "ndcg_at_k": 0.1022,
    "timings_ms": {
      "retrieval": {
        "p50": 394.74,
        "p95": 399.39
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "numeric": {
    "questions": 10,
    "successful_requests": 10,
    "answerable_questions": 10,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.6,
    "source_recall_at_k": 0.9,
    "chunk_recall_at_1": 0.3,
    "chunk_recall_at_k": 0.6,
    "mrr_at_k": 0.4167,
    "ndcg_at_k": 0.4631,
    "timings_ms": {
      "retrieval": {
        "p50": 396.37,
        "p95": 404.35
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "paraphrase": {
    "questions": 10,
    "successful_requests": 10,
    "answerable_questions": 10,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.7,
    "source_recall_at_k": 1.0,
    "chunk_recall_at_1": 0.2,
    "chunk_recall_at_k": 0.7,
    "mrr_at_k": 0.5833,
    "ndcg_at_k": 0.6393,
    "timings_ms": {
      "retrieval": {
        "p50": 390.49,
        "p95": 401.77
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
    "questions": 19,
    "successful_requests": 19,
    "answerable_questions": 19,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.6842,
    "source_recall_at_k": 0.9474,
    "chunk_recall_at_1": 0.2632,
    "chunk_recall_at_k": 0.6842,
    "mrr_at_k": 0.5789,
    "ndcg_at_k": 0.6226,
    "timings_ms": {
      "retrieval": {
        "p50": 390.25,
        "p95": 18505.71
      },
      "chat": {
        "p50": null,
        "p95": null
      }
    }
  },
  "test": {
    "questions": 12,
    "successful_requests": 12,
    "answerable_questions": 12,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.5833,
    "source_recall_at_k": 0.8333,
    "chunk_recall_at_1": 0.0833,
    "chunk_recall_at_k": 0.5833,
    "mrr_at_k": 0.2917,
    "ndcg_at_k": 0.3661,
    "timings_ms": {
      "retrieval": {
        "p50": 390.49,
        "p95": 404.35
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
    "questions": 31,
    "successful_requests": 31,
    "answerable_questions": 31,
    "refusal_questions": 0,
    "isolation_questions": 0,
    "isolation_leakage_rate": null,
    "evidence_complete_at_k": 0.6452,
    "source_recall_at_k": 0.9032,
    "chunk_recall_at_1": 0.1935,
    "chunk_recall_at_k": 0.6452,
    "mrr_at_k": 0.4677,
    "ndcg_at_k": 0.5233,
    "timings_ms": {
      "retrieval": {
        "p50": 390.49,
        "p95": 404.35
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
|HR-10|hr|paraphrase|answerable|True|False|0.0|-|-|
|HR-11|hr|paraphrase|answerable|True|True|1.0|-|-|
|HR-12|hr|paraphrase|answerable|True|True|0.5|-|-|
|HR-13|hr|paraphrase|answerable|True|True|0.5|-|-|
|HR-14|hr|paraphrase|answerable|True|False|1.0|-|-|
|HR-15|hr|paraphrase|answerable|True|True|0.5|-|-|
|HR-16|hr|paraphrase|answerable|True|True|1.0|-|-|
|HR-17|hr|paraphrase|answerable|True|True|0.3333|-|-|
|HR-18|hr|paraphrase|answerable|True|True|1.0|-|-|
|HR-19|hr|numeric|answerable|True|False|0.0|-|-|
|HR-20|hr|numeric|answerable|True|False|0.0|-|-|
|HR-21|hr|numeric|answerable|True|False|0.0|-|-|
|HR-22|hr|numeric|answerable|False|False|0.0|-|-|
|HR-23|hr|numeric|answerable|True|True|1.0|-|-|
|HR-24|hr|numeric|answerable|True|True|1.0|-|-|
|HR-25|hr|numeric|answerable|True|True|1.0|-|-|
|HR-26|hr|numeric|answerable|True|True|0.5|-|-|
|HR-27|hr|numeric|answerable|True|True|0.3333|-|-|
|HR-28|hr|numeric|answerable|True|True|0.3333|-|-|
|HR-29|hr|multi_source|answerable|True|False|0.3333|-|-|
|HR-30|hr|multi_source|answerable|False|False|0.0|-|-|
|HR-31|hr|multi_source|answerable|False|False|0.0|-|-|

## 人工复核

逐题核对答案正确性与原文支持程度；未复核题目的人工分数留空。

### HR-01 每个月几号发工资？遇到周末会提前吗？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：薪酬结构与发薪日历说明.md

检索来源：薪酬结构与发薪日历说明.md, 薪酬结构与发薪日历说明.md, 薪酬结构与发薪日历说明.md

参考：每月 15 日发放上一个自然月的工资；遇法定节假日或双休日提前至最近一个工作日。

实际：未调用生成

引用：无

人工结论：待复核

### HR-02 公积金公司和个人各交多少？

难度：easy ｜ 库：hr ｜ split：test

标注来源：社会保险与住房公积金管理办法.md

检索来源：社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md

参考：公司与个人缴存比例均为 12%，缴存基数与社保基数一致。

实际：未调用生成

引用：无

人工结论：待复核

### HR-03 婚假有几天？什么时候必须休完？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：请假与休假管理制度.md

检索来源：请假与休假管理制度.md, 员工关系与假期常见问题 FAQ.md, 请假与休假管理制度.md

参考：婚假 10 个自然日，须在领取结婚证之日起 12 个月内休完。

实际：未调用生成

引用：无

人工结论：待复核

### HR-04 公司年度体检的标准是多少钱？

难度：easy ｜ 库：hr ｜ split：test

标注来源：补充医疗保险与年度体检福利说明.md

检索来源：补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md, 补充医疗保险与年度体检福利说明.md

参考：1200 元/人；40 周岁及以上员工为 2000 元/人。

实际：未调用生成

引用：无

人工结论：待复核

### HR-05 春节公司发什么福利？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：节日福利与团建经费管理办法.md

检索来源：节日福利与团建经费管理办法.md, 节日福利与团建经费管理办法.md, 节日福利与团建经费管理办法.md

参考：800 元/人的实物礼包加平台积分。

实际：未调用生成

引用：无

人工结论：待复核

### HR-06 辞职要提前多久通知公司？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：离职管理与工作交接流程.md

检索来源：离职管理与工作交接流程.md, 员工关系与假期常见问题 FAQ.md, 离职管理与工作交接流程.md

参考：正式员工须提前 30 日书面通知；试用期员工提前 3 日。

实际：未调用生成

引用：无

人工结论：待复核

### HR-07 公司账号密码多久要换一次？

难度：easy ｜ 库：hr ｜ split：test

标注来源：信息安全与数据保密规范.md

检索来源：信息安全与数据保密规范.md, 关于启用新版考勤与请假制度的通知.md, 员工关系与假期常见问题 FAQ.md

参考：每 90 天更换一次，且不得与前 5 次使用过的密码重复。

实际：未调用生成

引用：无

人工结论：待复核

### HR-08 签 3 年期限的劳动合同，试用期是多久？

难度：easy ｜ 库：hr ｜ split：dev

标注来源：员工入职办理指南.md

检索来源：新员工试用期管理与转正流程.md, 员工入职办理指南.md, 病假管理与医疗期说明.md

参考：试用期为 3 个月，试用期工资按定薪的 90% 发放。

实际：未调用生成

引用：无

人工结论：待复核

### HR-09 我早上晚打卡了十几分钟，会被扣多少钱？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：考勤管理与打卡规范.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 考勤管理与打卡规范.md

参考：迟到 30 分钟以内每次扣发当月工资 50 元；超过 30 分钟按事假半天计。

实际：未调用生成

引用：无

人工结论：待复核

### HR-10 忘记打卡的话，一个月最多能补几次？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：考勤管理与打卡规范.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 关于启用新版考勤与请假制度的通知.md

参考：每月最多补卡 3 次，须在事发后 24 小时内提交。

实际：未调用生成

引用：无

人工结论：待复核

### HR-11 以前那份差旅住宿标准是不是作废了？现在按哪个文件执行？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：关于调整 2026 年度差旅住宿标准的通知.md

检索来源：关于调整 2026 年度差旅住宿标准的通知.md, 关于调整 2026 年度差旅住宿标准的通知.md, 差旅报销标准（其他城市）.md

参考：《差旅报销标准（2024 版）》自 2026 年 1 月 1 日起废止，现行以《差旅报销标准（一线城市）》与《差旅报销标准（其他城市）》为准。

实际：未调用生成

引用：无

人工结论：待复核

### HR-12 我们部门团建一年人均能花多少钱？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：餐饮与团建费用报销口径.md

检索来源：餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md, 餐饮与团建费用报销口径.md

参考：每人每季度 200 元，全年每人累计不超过 800 元。

实际：未调用生成

引用：无

人工结论：待复核

### HR-13 我每年买办公用品的预算是多少？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：办公用品采购与报销标准.md

检索来源：办公用品采购与报销标准.md, 办公用品采购与报销标准.md, 办公用品采购与报销标准.md

参考：1200 元/人，超出部分须部门负责人审批。

实际：未调用生成

引用：无

人工结论：待复核

### HR-14 周末值班能不能像加班那样换成调休？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：值班与加班补贴说明.md

检索来源：值班与加班补贴说明.md, 值班与加班补贴说明.md, 加班与调休管理办法.md

参考：不能。值班只发补贴，休息日值班 300 元/次，不折算调休；只有被认定为加班的部分才能按倍数折算调休。

实际：未调用生成

引用：无

人工结论：待复核

### HR-15 绩效评级里拿 S 的人大概占多少比例？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：绩效考核管理办法.md

检索来源：绩效考核管理办法.md, 绩效考核管理办法.md, 绩效评级与结果应用说明.md

参考：S 级 10%，A 级 25%，B 级 50%，C 级 12%，D 级 3%。

实际：未调用生成

引用：无

人工结论：待复核

### HR-16 连续两个季度评 D 会有什么后果？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：绩效评级与结果应用说明.md

检索来源：绩效评级与结果应用说明.md, 绩效评级与结果应用说明.md, 绩效考核管理办法.md

参考：进入为期 3 个月的绩效改进计划（PIP）。

实际：未调用生成

引用：无

人工结论：待复核

### HR-17 竞业限制一般要持续多久？补偿怎么算？

难度：paraphrase ｜ 库：hr ｜ split：test

标注来源：离职证明与竞业限制说明.md

检索来源：离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md, 离职证明与竞业限制说明.md

参考：期限最长不超过 12 个月；补偿为离职前 12 个月平均工资的 30%，按月发放。

实际：未调用生成

引用：无

人工结论：待复核

### HR-18 提交申诉后多久能拿到结果？

难度：paraphrase ｜ 库：hr ｜ split：dev

标注来源：员工申诉与投诉处理流程.md

检索来源：员工申诉与投诉处理流程.md, 员工申诉与投诉处理流程.md, 绩效考核管理办法.md

参考：受理时限 3 个工作日，自受理之日起 15 个工作日内给出书面结论。

实际：未调用生成

引用：无

人工结论：待复核

### HR-19 去上海出差，住宿一晚最多能报销多少钱？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：差旅报销标准（一线城市）.md

检索来源：差旅报销标准（一线城市）.md, 报销与出差常见问题 FAQ.md, 差旅报销标准（一线城市）.md

参考：600 元/晚，据实报销，超出部分由员工自理。

实际：未调用生成

引用：无

人工结论：待复核

### HR-20 去成都出差，住宿每晚的上限是多少？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：差旅报销标准（其他城市）.md

检索来源：关于调整 2026 年度差旅住宿标准的通知.md, 差旅报销标准（其他城市）.md, 差旅报销标准（一线城市）.md

参考：450 元/晚。

实际：未调用生成

引用：无

人工结论：待复核

### HR-21 我在公司干了 6 年，年假能有几天？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：请假类型与假期额度对照表.md

检索来源：员工关系与假期常见问题 FAQ.md, 请假与休假管理制度.md, 请假类型与假期额度对照表.md

参考：15 天。

实际：未调用生成

引用：无

人工结论：待复核

### HR-22 病假超过 5 天以后，工资按几成发？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：请假类型与假期额度对照表.md

检索来源：病假管理与医疗期说明.md, 病假管理与医疗期说明.md, 病假管理与医疗期说明.md

参考：超出 5 天的部分按本人日工资的 60% 计发。

实际：未调用生成

引用：无

人工结论：待复核

### HR-23 加班换来的调休多久不用就会作废？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：加班与调休管理办法.md

检索来源：加班与调休管理办法.md, 加班与调休管理办法.md, 加班与调休管理办法.md

参考：自加班发生之日起 6 个月，逾期自动作废，不予折现。

实际：未调用生成

引用：无

人工结论：待复核

### HR-24 一笔 4800 元的差旅报销要走谁的审批？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：费用报销审批权限表.md

检索来源：费用报销审批权限表.md, 费用报销审批权限表.md, 费用报销审批权限表.md

参考：属 1000 元（含）至 5000 元档，由直属主管与部门负责人审批。

实际：未调用生成

引用：无

人工结论：待复核

### HR-25 我们部门要添置一套约 3 万元的测试设备，审批流程要走到哪一级？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：采购与付款审批权限表.md

检索来源：采购与付款审批权限表.md, 报销与出差常见问题 FAQ.md, 采购与付款审批权限表.md

参考：属 5000 元（含）至 50000 元档，由部门负责人、采购负责人与财务负责人审批。

实际：未调用生成

引用：无

人工结论：待复核

### HR-26 2026 年社保缴费基数的上下限是多少？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：社会保险与住房公积金管理办法.md

检索来源：社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md, 社会保险与住房公积金管理办法.md

参考：上限 35283 元/月，下限 6821 元/月。

实际：未调用生成

引用：无

人工结论：待复核

### HR-27 P6 员工的年终奖基数是几个月工资？

难度：numeric ｜ 库：hr ｜ split：test

标注来源：年终奖与绩效奖金发放办法.md

检索来源：年终奖与绩效奖金发放办法.md, 年终奖与绩效奖金发放办法.md, 年终奖与绩效奖金发放办法.md

参考：2 个月固定薪资。

实际：未调用生成

引用：无

人工结论：待复核

### HR-28 转正评估一般是什么时候启动？

难度：numeric ｜ 库：hr ｜ split：dev

标注来源：新员工试用期管理与转正流程.md

检索来源：新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md, 新员工试用期管理与转正流程.md

参考：试用期届满前 10 个工作日启动转正评估。

实际：未调用生成

引用：无

人工结论：待复核

### HR-29 去上海出差 3 天 2 晚，补贴和住宿分别按什么标准算？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：出差管理办法.md, 差旅报销标准（一线城市）.md

检索来源：差旅报销标准（一线城市）.md, 出差管理办法.md, 出差管理办法.md

参考：出差补贴 150 元/天（出发与返回当日各按半天计）；住宿上限 600 元/晚据实报销。两份文件各提供一半口径。

实际：未调用生成

引用：无

人工结论：待复核

### HR-30 年假没休完能折成钱吗？在职和离职有区别吗？

难度：multi_source ｜ 库：hr ｜ split：test

标注来源：请假与休假管理制度.md, 请假类型与假期额度对照表.md

检索来源：年终奖与绩效奖金发放办法.md, 请假与休假管理制度.md, 离职管理与工作交接流程.md

参考：在职员工可在次年 3 月 31 日前申请折现，每年最多 5 天；离职时当年度应休未休年假按日工资 100% 折现，同样最多 5 天。

实际：未调用生成

引用：无

人工结论：待复核

### HR-31 加班到晚上十一点打车回家，这笔钱怎么报？

难度：multi_source ｜ 库：hr ｜ split：dev

标注来源：加班与调休管理办法.md, 日常费用报销管理办法.md

检索来源：考勤管理与打卡规范.md, 考勤管理与打卡规范.md, 差旅报销标准（其他城市）.md

参考：加班至 22:00 之后可据实报销当日自公司至居住地的打车费，单次上限 120 元。

实际：未调用生成

引用：无

人工结论：待复核
