# 中文导读：
# 相邻文本块扩展：围绕召回锚点补充同文档版本的上下文，并限制数量；扩展前仍需复核版本是否有权访问和可检索

"""Bounded adjacent context from the same indexed document version as trusted search hits."""

from sqlalchemy import select, tuple_

from app.adapters.vectorstore.milvus import collection_name
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)

# 生成上下文最多保留 8 个块，这是数量上限，不是字符数或 token 预算。
MAX_CONTEXT_CHUNKS = 8


# 保留召回锚点，并仅扩展同一授权版本内的邻块；数量上限避免提示词无限增长。
# 调用前提：hits 必须来自已经完成权限过滤的 search；本函数没有用户身份参数。
# allowed 只约束邻块与这些可信锚点的归属一致，并不是独立的用户授权检查。
def expand_neighbors(hits, db):
    # 按召回顺序截取锚点；锚点为空或已占满容量时不再查询数据库。
    anchors = hits[:MAX_CONTEXT_CHUNKS]
    if not anchors or len(anchors) >= MAX_CONTEXT_CHUNKS:
        return anchors
    # 先保留全部锚点，邻块只填剩余位置，不能把命中的证据挤出上下文。
    # Keep all search anchors first; never displace a retrieved hit with its neighbor.
    wanted = []
    # 用版本、文档、知识库三元组限制补全范围，避免只凭位置匹配到其他文档。
    allowed = {(h["version_id"], h["document_id"], h["knowledge_base_id"]) for h in anchors}
    # 按“所有前一块，再所有后一块”的顺序收集候选；位置从 0 开始，过滤负数并去重。
    for offset in [-1, 1]:
        for hit in anchors:
            key = (hit["version_id"], hit["position"] + offset)
            if key[1] >= 0 and key not in wanted:
                wanted.append(key)
    # 一次 SQL 批量读取候选邻块，复核当前版本、审核与当前向量集合的索引状态。
    rows = db.execute(
        select(Chunk, Document, KnowledgeBase.name)
        .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
        .join(Document, DocumentVersion.document_id == Document.id)
        .join(KnowledgeBase, Document.knowledge_base_id == KnowledgeBase.id)
        .join(VectorIndex, VectorIndex.version_id == DocumentVersion.id)
        .where(
            tuple_(Chunk.version_id, Chunk.position).in_(wanted),
            DocumentVersion.status == "parsed",
            DocumentVersion.is_current.is_(True),
            DocumentVersion.review_status == "approved",
            VectorIndex.collection == collection_name(),
            VectorIndex.status == "indexed",
        )
    ).all()
    # SQL 返回顺序不保证与候选顺序一致，先建映射，再按 wanted 的顺序组装。
    by_key = {}
    for chunk, doc, kb_name in rows:
        # 再次核对锚点归属；不能因为版本号或邻接位置相同就接受候选。
        if (chunk.version_id, doc.id, doc.knowledge_base_id) not in allowed:
            continue
        by_key[(chunk.version_id, chunk.position)] = {
            "chunk_id": chunk.id,
            "document_id": doc.id,
            "version_id": chunk.version_id,
            "knowledge_base_id": doc.knowledge_base_id,
            "knowledge_base_name": kb_name,
            "filename": doc.filename,
            "position": chunk.position,
            "page": chunk.page,
            "content": chunk.content,
            # 标记这是补全证据；没有新增向量分数，因为它不是相似度召回命中。
            "context_role": "neighbor",
        }
    # 返回顺序是锚点在前、邻块在后，并非全文顺序；复制字典以免修改输入命中。
    result = [{**h, "context_role": "retrieved"} for h in anchors]
    # 一个邻块可能同时被多个锚点指向，按 chunk_id 去重后再计入容量。
    seen = {h["chunk_id"] for h in anchors}
    for key in wanted:
        hit = by_key.get(key)
        if hit and hit["chunk_id"] not in seen:
            result.append(hit)
            seen.add(hit["chunk_id"])
        # 达到总块数限制立即停止，避免相邻补全无限扩大提示词。
        if len(result) >= MAX_CONTEXT_CHUNKS:
            break
    return result
