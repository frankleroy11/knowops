"""向量索引适配器：真实实现见 milvus.MilvusStore。

注意：base.py 里保存的是本阶段最初的接口草案（IndexedChunk/SearchHit/VectorStore 协议），
最终实现改为 MySQL 保存正文 + Milvus 只存 chunk_id 与过滤字段，接口因此不同。
保留该文件仅为记录设计取舍，**不要**按它编码；以 milvus.py 为准。
"""

from app.adapters.vectorstore.milvus import MilvusStore, collection_name

__all__ = ["MilvusStore", "collection_name"]
