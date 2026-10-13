import hashlib
import json

from pymilvus import DataType, MilvusClient

from app.core.config import get_settings


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
        self.client = MilvusClient(uri=get_settings().milvus_uri, timeout=10)

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

    def upsert(self, rows):
        self.client.upsert(self.name, rows)

    def search(self, vector, kb_id, limit):
        if not self.client.has_collection(self.name):
            return []
        if isinstance(kb_id, list):
            if not kb_id:
                return []
            expression = "knowledge_base_id in [" + ",".join(str(int(i)) for i in kb_id) + "]"
        else:
            expression = f"knowledge_base_id == {int(kb_id)}"
        return self.client.search(
            self.name,
            [vector],
            filter=expression,
            limit=limit,
            search_params={"metric_type": "COSINE", "params": {"ef": 64}},
        )[0]

    def close(self):
        self.client.close()
