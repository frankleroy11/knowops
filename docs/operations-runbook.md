# KnowOps 本机部署与运维

## 启动与配置

项目根目录执行 README 中启动流程。宿主机 Conda `knowops` 运行 API 与 solo Worker；Docker Compose 运行 MySQL/Redis/Milvus/etcd/MinIO，可选 Attu。首次复制 `.env.example`，填写密码与 Qwen 配置，缓存 BGE-M3 后可以开启 EMBEDDING_OFFLINE=1。执行 Alembic 至 0011，再构建前端。

认证正常使用 `AUTH_MODE=enforced`。首次运行 `PYTHONPATH=. python scripts/bootstrap_admin.py`；管理员密码仅保存在 `.tmp/local-admin-credentials.json`（0600）。已有启用的平台管理员时不会重置密码。只在本机读取，用后可以删除本地明文凭据文件；登录后通过安全设置修改为自选密码。不要把密码写到命令行、聊天或 Git。

本次本机启动采用 API 127.0.0.1:8010，以及唯一 `knowops-kb@%h` Worker。配置或任务代码更新后要重启；API reload 不会重启 Worker。不要启动多个同名 Worker。所有基础服务仅绑定回环地址，公网部署另需 TLS、反向代理、网络隔离、密钥管理、持久化备份和容量验收，此配置不代表生产上线。

## 备份

MySQL 是业务、正文、权限与版本权威，`storage/` 是原始上传文件，Milvus 是可重建副本。

1. 进入维护窗口，暂停用户写入并停止该项目 API 和所有该项目 Worker。用进程命令及 cwd 确认归属，不要停止其他项目服务。
2. 保留数据库容器运行，执行：

```bash
PYTHONPATH=. python scripts/backup_local.py --output .tmp/backups/YYYYMMDD-HHMMSS --writers-stopped
```

3. 生成 `mysql.sql`、`storage.tar.gz`、`manifest.json`，目录权限 0700，SQL/压缩包 0600。manifest 含 SHA-256；`--writers-stopped` 是操作者确认，脚本不会替你证明所有外部写入均已停止。
4. 在本机验证校验和后，另行将备份加密存入受控位置。备份含文档、口令摘要与 Token 摘要，不入 Git。`.env` 与模型权重未纳入备份，需另行安全保存配置和恢复来源。
5. 重启 API 与唯一 Worker，验证 readiness、登录和临时文档流程。

此方案不是在线分布式快照。不在存在用户写入时运行，不对 Milvus/Redis 数据目录做未经验证的热拷贝。

## 恢复

先在隔离 MySQL 数据库和临时文件目录做演练，核对所有表记录数及上传文件哈希。**不可直接把演练 SQL 导入当前业务库。**

正式恢复需单独维护窗口：停止 API/Worker，保存现状备份，核验备份校验和；导入 SQL 至目标库，恢复 storage/ 至该项目目录。归档只允许 `storage/` 内的普通文件/目录，拒绝路径穿越和外部符号链接；仅恢复可信的本项目归档。核对 Alembic 版本和配置。

Milvus 没有包含在本备份中，恢复后不能相信 SQL 中旧的 indexed 标记：在离线状态下将**目标嵌入集合**的 VectorIndex 状态改为 failed，再将 parsed 版本逐个投递 index_document。已有向量可按 chunk_id 幂等覆盖；为彻底避免孤儿向量，建议恢复到新的专用 `MILVUS_COLLECTION_PREFIX`，再全部重建（新集合自动创建对应索引记录）。旧集合保留至恢复验收结束后再由管理员决定清理。不要直接删除共享集合或其他项目数据。

若 Redis 保留了旧任务，先停止旧 Worker，并使用新的 Redis DB/专用实例恢复队列，避免重放旧版本 ID。不要对共享 Redis 执行 FLUSHALL。逐个验证解析、索引、权限、检索和答案后才开放用户流量。

本次演练：已将真实 SQL 备份导入一次性独立数据库、上传归档解到临时目录，核对表记录数与文件哈希后清理演练副本。**未执行当前业务库覆盖恢复或全量 Milvus 重建**。

## 故障排查

| 现象 | 检查与处理 |
|---|---|
| 登录页无管理员 | 本机读取 bootstrap 文件；已有账号不自动重置。使用项目 CLI 恢复须明确目标账号。 |
| ready 返回 503 | 按 mysql/redis/milvus 项检查容器、宿主机端口和日志；不要输出 .env。 |
| Worker 待确认 | solo 长任务期间可能不响应控制通道；查进程、日志和数据库状态，不能直接判定离线。 |
| 解析 failed | 管理控制台失败任务页定位；非法 UTF-8 或扫描 PDF 修正后上传新版本，单纯重试无效。 |
| 索引 failed | 检查模型缓存、MPS/内存和 Milvus；确认不在运行后重试索引。 |
| pending/indexing 长时间不变 | 先确认所有 Worker/队列和活动任务；当前没有自动租约回收，需明确确认旧任务已停止后人工恢复失败状态，禁止并行强制重试。 |
| parsed 但无法问答 | 检查 indexed、当前版本、审核通过、文档未下架及账号权限。 |
| 资料已召回仍拒答 | 记录问题、命中原文和 grounding_status；这是生成/问题口径问题，不应伪造引用或把拒答当检索故障。 |
| 删除 503 | 部分向量可能已清理，但 SQL/文件可能保留，重新确认原对象后重试。 |
| file_cleanup_pending > 0 | 执行 storage_gc.py dry-run，只确认本项目明确的孤儿文件再回收。 |
| Attu 正常但 Milvus URL 404 | Milvus 接口端口无网页首页；使用 Attu 8000。 |

## 演示与交付顺序

1. 用管理员登录，展示工作台/控制台边界与系统状态。
2. 创建演示知识库、编辑者、只读成员；配置上传需审核。
3. 编辑者上传合成制度；只读成员在审核前检索不到，审核后提问得到引用。
4. 上传新版本、审核、切换有效版本，展示旧版本不参与检索。
5. 上传无效样例展示失败定位，再上传修正版本；删除演示文档展示清理。
6. 展示开发评测结果、失败案例和延迟，说明引文精确匹配不等于答案语义正确。

Git 按功能分支、PR、CI 开发；合并使用 merge commit 保留现有提交与上下游祖先关系。依赖 PR 依次将 base 改为 main，核对差异和 CI 后合并，不强推历史。
