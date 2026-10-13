# KnowOps 固定评估集

运行（API、Worker 和基础服务需已启动）：

```bash
conda activate knowops
python scripts/evaluate.py
```

每次运行创建两个独立演示知识库并上传 6 份合成资料，保留数据库、文件和索引数据。
主库 5 份资料，隔离库 1 份；30 个问题均在主库提问，隔离题的答案只存在于隔离库。
数据文件：questions.json；资料：corpus/。未来比较优化应保持资料、问题、top_k 和模型配置一致。

输出在 runs/<北京时间>/：metadata.json、results.json、report.md。
记录模型标识、集合、Git 提交、工作区是否有修改、题集和语料哈希，不记录密钥。
results.json 保留检索来源、回答、引用及人工评分占位。report.md 支持逐题复核。
中途失败也会保留已完成题目，但总指标只覆盖已完成题目；请检查 questions 是否为 30。

## 指标口径

- source_recall_at_3：有答案题的前 3 个检索结果是否包含全部标注来源文档；按文档级统计。
- refusal_accuracy：无答案和隔离题是否返回 answerable=false 且无引用。
- citation_source_match_rate：有答案题的引用文件集合是否与标注来源匹配，不代表逐句事实正确。
- answerable_response_rate：有答案题是否返回可回答，不等于回答正确率。
- keyword_pass_rate_heuristic_only：预设关键词筛查，仅作人工复核线索，不能作为正确率。
- timings_ms：问答接口内部检索、生成和总耗时；统计成功请求的 p50/p95（最近秩）。
- HTTP 错误计入对应题型的失败；另外报告 successful_requests。

固定题集来自人工编写的虚构制度，样本量小、语料简单。不能把本次结果作为真实企业准确率，
也不能据此宣称普遍优于其他模型。尚未引入自动 LLM 裁判。
API 仍为单轮问答，针对提示注入的拒答样例不构成安全保证。
