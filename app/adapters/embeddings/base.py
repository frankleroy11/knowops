"""Embedding 适配器契约。

稳定的对外契约只有三件事：模型标识 model_name、向量维度 dim、归一化策略 normalized。
三者共同决定 Milvus collection 的命名，因此切换模型不会污染既有索引。
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


class EmbeddingError(RuntimeError):
    """模型缺失、权重损坏或推理失败时抛出，由上层转换为可读状态。"""


@runtime_checkable
class Embedder(Protocol):
    model_name: str
    dim: int
    normalized: bool

    def encode(self, texts: Sequence[str], *, is_query: bool = False) -> list[list[float]]:
        """把文本编码为向量。

        必须满足：len(result) == len(texts)，每个向量长度为 dim 且元素为 float。
        is_query 用于区分查询与文档（本阶段 BGE-M3 未使用该提示，保留扩展点）。
        """
        ...


def l2_normalize(vector: Sequence[float]) -> list[float]:
    """L2 归一化；零向量原样返回，避免除零。"""
    norm = sum(float(value) * float(value) for value in vector) ** 0.5
    if norm == 0.0:
        return [float(value) for value in vector]
    return [float(value) / norm for value in vector]
