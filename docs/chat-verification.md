# Qwen 问答验证

2026-10-13，Conda knowops。

- 使用被忽略的本地 .env 配置 Qwen Plus，通过 OpenAI 兼容协议调用；未输出或提交密钥。
- 真实 Qwen 调用：依据 VPN 账号申请资料生成答案，返回 source_ids=[1]。
- 真实资料不足调用：问题为餐费报销标准，资料只有 VPN，返回 answerable=false 和空引用。
- Ruff 通过，pytest 16 passed。
- 新增测试覆盖无上下文不调用模型、伪造引用、拒答、引用去重、后端来源映射、服务失败和 HTTP 协议。

接口 POST /api/v1/chat/ask，详细操作见 README。
当前为单轮问答，无鉴权、历史会话、流式输出或系统评估。
引用编号校验只验证来源存在，未实现逐句事实核验。

完整真实 HTTP 链路已验证：

- “在家办公如何连接公司内网？”返回 200、answerable=true；
  答案说明使用公司账号登录 VPN，引用 VPN使用说明.md、chunk_id=7。
- “公司报销餐费的标准是多少？”返回 200、answerable=false、citations=[]。

上述为两条功能验收，不是整体准确率或抗提示注入评估。
