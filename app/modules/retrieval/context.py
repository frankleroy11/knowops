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

MAX_CONTEXT_CHUNKS = 8


# 保留召回锚点，并仅扩展同一授权版本内的邻块；数量上限避免提示词无限增长。
def expand_neighbors(hits, db):
    anchors = hits[:MAX_CONTEXT_CHUNKS]
    if not anchors or len(anchors) >= MAX_CONTEXT_CHUNKS:
        return anchors
    # Keep all search anchors first; never displace a retrieved hit with its neighbor.
    wanted = []
    allowed = {(h["version_id"], h["document_id"], h["knowledge_base_id"]) for h in anchors}
    for offset in [-1, 1]:
        for hit in anchors:
            key = (hit["version_id"], hit["position"] + offset)
            if key[1] >= 0 and key not in wanted:
                wanted.append(key)
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
    by_key = {}
    for chunk, doc, kb_name in rows:
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
            "context_role": "neighbor",
        }
    result = [{**h, "context_role": "retrieved"} for h in anchors]
    seen = {h["chunk_id"] for h in anchors}
    for key in wanted:
        hit = by_key.get(key)
        if hit and hit["chunk_id"] not in seen:
            result.append(hit)
            seen.add(hit["chunk_id"])
        if len(result) >= MAX_CONTEXT_CHUNKS:
            break
    return result
