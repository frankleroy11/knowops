# LangChain 问答生成链路

## 接入范围

使用 `langchain-core` 的 `RunnableLambda`、`ChatPromptTemplate` 和管道运算符组合生成流程。无需安装包含更多集成的完整 `langchain` 包。

```text
已授权的检索结果
  → prompt_inputs：序列化问题、原文与合法来源编号
  → ChatPromptTemplate：构造 system / human 消息
  → invoke_qwen：调用兼容 OpenAI 的 Qwen HTTP 接口
  → parse_answer：严格解析完整 JSON 对象
  → 原有 ModelAnswer 校验和逐条引用核验
```

代码入口为 `app/adapters/llm/qwen.py` 的 `generate_grounded_answer`。接口签名及返回格式保持一致，问答路由继续使用该入口。

检索仍由 `app/modules/retrieval/` 执行：SQL 授权及版本筛选、Milvus 过滤、可选重排与相邻块扩展均保留原有实现。本次没有替换为 LangChain 的通用 Retriever，也没有加入知识图谱或 Agent。

## 为什么保留 HTTP 适配器

Runnable 支持封装现有函数，无需同步改成模型厂商 SDK。现有调用约定继续使用配置中的 `LLM_MODEL`、`LLM_BASE_URL`、`LLM_API_KEY`，温度 0、最多 1200 个输出 token、非流式、连接超时 10 秒、HTTP 超时 60 秒。本次不新增自动重试。

官方接口依据：[Runnable 组合](https://reference.langchain.com/python/langchain-core/runnables/base)、[ChatPromptTemplate](https://reference.langchain.com/python/langchain-core/prompts/chat/ChatPromptTemplate)。

## 关键约束

- 证据以模板变量值插入；文档中的花括号不会成为新的模板变量。
- 保留合法来源 ID 列表，模型不得按数组位置另造编号。
- JSON 解析不自动补全截断内容；非对象 JSON、解析失败或 HTTP 错误统一转为模型不可用，由问答路由返回 503。
- 完整 JSON 不等于有效答案。原有 Pydantic 字段验证、证据不足拒答和逐条摘录校验继续执行。
- 使用 `tracing_context(enabled=False)` 关闭这一调用范围内的 LangSmith 外部追踪，避免环境级追踪设置上传问题和原文。`langsmith` 是本地依赖，不需要配置追踪账号或密钥。
- 接入框架不构成准确率提升证据，本次未进行新的在线 Qwen 质量评测。

## 安装和验证

```bash
python -m pip install -r requirements.txt
python -m pip check
ruff check .
python -m pytest -q
```

新增 `tests/test_langchain_generation.py`，使用真实 Runnable 链和 HTTP MockTransport 检查字面量证据、非连续来源编号、代码围栏 JSON、截断／非法输出、供应商错误脱敏、无自动重试、追踪关闭和缺配置提前失败。原有问答测试覆盖引用校验与拒答逻辑。离线测试不调用收费模型。

部署时 API 环境需要安装更新后的依赖并重启。解析和索引任务实现没有变动；在其他机器部署时也应按统一依赖文件安装环境。
