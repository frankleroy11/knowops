# 中文导读：
# Milvus 向量存储适配层
# 集合名称包含编码配置指纹；知识库和版本过滤在向量查询时执行，正文与业务状态仍以 MySQL 为准

import hashlib
import json
from uuid import uuid4

from pymilvus import DataType, MilvusClient

from app.core.config import get_settings


# 把模型、维度、截断长度和归一化策略纳入集合标识，防止不兼容向量混用。
def collection_name():
    s = get_settings()
    # Include truncation policy: changing it changes embeddings too.
    identity = [
        s.embedder_provider,
        s.embedding_model,
        s.embedding_dim,
        s.embedding_max_length,
        "l2",
        "cosine",
    ]
    digest = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:16]
    return f"{s.milvus_collection_prefix}_{digest}"


class MilvusStore:
    def __init__(self):
        self.name = collection_name()
        self.client = MilvusClient(
            uri=get_settings().milvus_uri, timeout=10, alias=f"knowops-{uuid4().hex}"
        )

    # 已有集合先核对维度；新集合以文本块 ID 为主键，使用余弦距离的 HNSW 索引。
    def ensure(self):
        if self.client.has_collection(self.name):
            info = self.client.describe_collection(self.name)
            vector = next(f for f in info["fields"] if f["name"] == "vector")
            if int(vector["params"]["dim"]) != get_settings().embedding_dim:
                raise ValueError("Milvus collection dimension mismatch")
            return
        schema = self.client.create_schema(auto_id=False, enable_dynamic_field=False)
        schema.add_field("chunk_id", DataType.INT64, is_primary=True)
        for field in ("knowledge_base_id", "document_id", "version_id"):
            schema.add_field(field, DataType.INT64)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=get_settings().embedding_dim)
        params = self.client.prepare_index_params()
        params.add_index(
            "vector",
            index_type="HNSW",
            metric_type="COSINE",
            params={"M": 16, "efConstruction": 200},
        )
        self.client.create_collection(
            self.name, schema=schema, index_params=params, consistency_level="Strong"
        )

    # 按稳定的文本块主键覆盖写入，使任务重投时不重复插入同一个块。
    def upsert(self, rows):
        self.client.upsert(self.name, rows)

    # 空授权范围直接返回空结果；过滤知识库与版本后再取近邻，避免先召回越权数据。
    def search(self, vector, kb_id, limit, *, version_ids=None):
        if not self.client.has_collection(self.name):
            return []
        if isinstance(kb_id, list):
            if not kb_id:
                return []
            expression = "knowledge_base_id in [" + ",".join(str(int(i)) for i in kb_id) + "]"
        else:
            expression = f"knowledge_base_id == {int(kb_id)}"
        if version_ids is not None:
            if not version_ids:
                return []
            expression += " and version_id in [" + ",".join(str(int(i)) for i in version_ids) + "]"
        return self.client.search(
            self.name,
            [vector],
            filter=expression,
            limit=limit,
            search_params={"metric_type": "COSINE", "params": {"ef": 64}},
        )[0]

    # 仅删除指定知识库的向量，历史集合由调用方指定，不删除共享集合本身。
    def delete_knowledge_base(self, kb_id, collection=None):
        name = collection or self.name
        if self.client.has_collection(name):
            self.client.delete(name, filter=f"knowledge_base_id == {int(kb_id)}")

    # 仅删除指定文档的向量；文件和业务表由知识库业务层继续清理。
    def delete_document(self, document_id, collection=None):
        name = collection or self.name
        if self.client.has_collection(name):
            self.client.delete(name, filter=f"document_id == {int(document_id)}")

    def close(self):
        self.client.close()
