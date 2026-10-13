"""向量索引存储契约（Milvus）。

设计要点：
- 主键即 MySQL ``chunks.id``（BIGINT）。同一个 chunk 反复写入是幂等 upsert，不会产生重复记录。
- 每次写入都携带知识库/文档/版本等标量元数据，检索时用表达式过滤限定知识库范围，
  再回 MySQL 取正文，保证 MySQL 始终是业务状态的唯一来源。
- collection 名称由模型标识、维度、归一化策略共同派生，切换模型即切换 collection。
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

#: 归一化向量统一使用 COSINE，分数区间约 [-1, 1]，越大越相似。
METRIC_TYPE = "COSINE"
#: 小规模本地数据的 HNSW 参数，够用且无需额外训练。
INDEX_PARAMS = {
    "index_type": "HNSW",
    "metric_type": METRIC_TYPE,
    "params": {"M": 16, "efConstruction": 200},
}
SEARCH_PARAMS = {"metric_type": METRIC_TYPE, "params": {"ef": 64}}
CONSISTENCY_LEVEL = "Strong"


@dataclass(frozen=True)
class IndexedChunk:
    """待写入 Milvus 的一条切片记录。"""

    chunk_id: int
    knowledge_base_id: int
    document_id: int
    version_id: int
    position: int
    page: int | None
    content: str
    vector: list[float]


@dataclass(frozen=True)
class SearchHit:
    """Milvus 检索结果；正文由上层回查 MySQL 获取。"""

    chunk_id: int
    score: float
    knowledge_base_id: int
    document_id: int
    version_id: int
    position: int
    page: int | None


@runtime_checkable
class VectorStore(Protocol):
    collection_name: str
    dim: int

    def ensure_collection(self) -> str:
        """确保 collection 存在且维度一致；返回 collection 名称。维度不一致必须抛异常。"""
        ...

    def upsert(self, chunks: Sequence[IndexedChunk]) -> int:
        """幂等写入；返回写入条数。空序列直接返回 0。"""
        ...

    def delete_version(self, version_id: int) -> int:
        """删除某版本的全部向量；返回删除条数（Milvus 可能返回 0，不得据此判断失败）。"""
        ...

    def delete_document(self, document_id: int) -> int:
        """删除某文档的全部向量。"""
        ...

    def search(
        self,
        vector: Sequence[float],
        *,
        limit: int,
        knowledge_base_ids: Sequence[int] | None = None,
    ) -> list[SearchHit]:
        """向量检索，可按知识库过滤；返回按 score 降序的命中列表。"""
        ...

    def count(self) -> int:
        """collection 中实体数量（collection 不存在时返回 0）。"""
        ...

    def close(self) -> None: ...
