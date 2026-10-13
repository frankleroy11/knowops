# Milvus 网页管理界面（Attu）

问答页面是 http://127.0.0.1:8010/ui/，向量管理页面是 http://127.0.0.1:8000/。
19540是Milvus接口端口，直接在浏览器打开根路径出现404不表示数据库连接失败。

## 启动和连接

```bash
docker compose --profile admin up -d attu
```

Attu使用已在Apple Silicon本机验证的zilliz/attu:v2.5.10，匹配当前Milvus2.5系列；
作为可选admin profile运行，端口只绑定127.0.0.1。
默认地址milvus:19530、数据库default，无需填写本机19540端口。
因为Attu后端也在Docker的knowops网络中，这里用容器服务名和容器端口。
宿主机Python客户端仍连接http://127.0.0.1:19540，两个地址指向同一个KnowOps实例。

页面点击“连接”后进入default数据库，再打开knowops_chunks_开头的当前集合：

- Schema：查看字段、1024维vector、HNSW/COSINE索引与加载状态。
- 数据：查看chunk_id、knowledge_base_id、document_id、version_id与向量数值。
- 向量搜索：用于直接查看向量检索结果；自然语言问答继续通过KnowOps页面完成。

Milvus保存向量和关联编号，文档正文在MySQL中，因此数据页不会直接展示整篇中文文档。
界面的Entity数量可能受统计刷新、插入与upsert/压缩影响，不将历史行数写成固定值。

本轮用已有镜像启动knowops-attu-1，页面确认已连通Milvus2.5.27、当前集合已加载，索引存在。
启动时使用--no-deps，只新增Attu，没有重建KnowOps数据库，也没有更改其他项目容器。
需要停止管理界面时：`docker compose --profile admin stop attu`；数据库仍独立运行。
