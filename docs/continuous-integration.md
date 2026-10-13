# 自动检查

`.github/workflows/ci.yml` 对每次push、pull_request和手动运行触发：

- Backend tests and lint：Python3.11，安装requirements-base.txt，运行Ruff和pytest。
- Frontend build：Node22，以package-lock.json执行npm ci及生产构建。

同一分支的新任务取消尚未结束的旧任务；Actions仅授予contents:read，不读取仓库密钥，不部署。
官方checkout/setup-python/setup-node固定到已核对的v6提交，避免版本标签静默变化。

requirements.txt仍是完整本机安装入口，包含requirements-base.txt和sentence-transformers。
CI只安装基础依赖，因为当前单元测试使用SQLite、模拟外部服务和假tokenizer，
真实模型在业务模块中延迟加载；CI禁止HuggingFace联网，不调用Qwen。
这些检查不代替MySQL/Milvus端到端测试、MPS推理和真实生成质量评估。

查看每次PR底部检查和仓库Actions页。失败时先修复，再合并。
此工作流本身不会强制阻止管理员合并；分支保护属于另一个仓库设置，不在本轮自动修改。
