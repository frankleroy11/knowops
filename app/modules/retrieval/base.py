"""语义检索契约与数据结构。"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class RetrievalError(RuntimeError):
    """检索不可用时抛出（索引缺失、模型不可用等），上层转换为可读错误。"""


@dataclass(frozen=True)
class RetrievedChunk:
    """检索结果：Milvus 提供相似度与定位信息，MySQL 提供权威正文。"""

    chunk_id: int
    score: float
    knowledge_base_id: int
    document_id: int
    version_id: int
    position: int
    page: int | None
    filename: str
    content: str


@runtime_checkable
class SemanticSearcher(Protocol):
    def search(
        self,
        query: str,
        *,
        knowledge_base_ids: Sequence[int] | None = None,
        limit: int = 5,
    ) -> list[RetrievedChunk]:
        """按语义相似度检索切片，按 score 降序返回。"""
        ...
