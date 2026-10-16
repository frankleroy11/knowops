# 中文导读：
# 向量索引业务：读取文本块、编码并按块标识写入 Milvus，再更新数据库状态
# 外部模型与向量写入在数据库锁之外执行，失败状态阻止残留向量参与检索

"""Embed and upsert one document version.

Database transactions are deliberately short: inputs are snapshotted first and results
are written last, so a slow embedding (model load, MPS, blocked network) never holds
row locks on `document_versions`. Holding `SELECT ... FOR UPDATE` across the embedding
call previously blocked review/publish writes for minutes on the same document.

Duplicate deliveries may embed twice; upserts are keyed by chunk_id, so the stored
result stays idempotent.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.embeddings.local import get_embedder
from app.adapters.vectorstore.milvus import MilvusStore, collection_name
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, VectorIndex

# 数据库保存可对用户展示的统一错误；详细堆栈只记录在服务端日志。
INDEX_ERROR = "索引失败：请检查模型缓存、设备及 Milvus 服务"


# 获取或暂存当前集合的索引状态对象；不在此处提交，事务由调用方负责。
def _job(db: Session, version_id: int) -> VectorIndex:
    job = db.scalar(
        select(VectorIndex).where(
            VectorIndex.version_id == version_id,
            VectorIndex.collection == collection_name(),
        )
    )
    # 编码配置变化会对应新集合，因此同一文档版本可以有不同集合的状态记录。
    if job is None:
        job = VectorIndex(version_id=version_id, collection=collection_name())
        db.add(job)
    return job


# 先记录索引中状态，再执行耗时编码与向量写入；最终成功才把数据库状态标为可用。
def index_version(version_id):
    # 第一阶段：短事务读取快照并标记 indexing；正常退出 begin 后提交并释放行锁。
    with SessionLocal.begin() as db:
        # 版本行锁串行化本阶段的状态检查，不会一直持有到模型加载和编码结束。
        version = db.scalar(
            select(DocumentVersion).where(DocumentVersion.id == version_id).with_for_update()
        )
        # 还没有可用文本块的版本不能建立索引，交由上游先完成解析。
        if version is None or version.status != "parsed":
            return {"status": "not_parsed"}
        job = _job(db, version_id)
        # 已有非空的完成记录就快速返回；重复投递不再编码这类版本。
        if job.status == "indexed" and job.chunks_indexed:
            return {"status": "indexed", "chunks": job.chunks_indexed}
        document = db.get(Document, version.document_id)
        if document is None:
            return {"status": "not_parsed"}
        document_id, knowledge_base_id = document.id, document.knowledge_base_id
        # 只复制编码所需的块 ID 和正文，按原文位置排序；离开会话后不再依赖 ORM 对象。
        rows = [
            (chunk.id, chunk.content)
            for chunk in db.scalars(
                select(Chunk).where(Chunk.version_id == version_id).order_by(Chunk.position)
            )
        ]
        job.status, job.error = "indexing", None

    # 第二阶段：在数据库事务之外进行模型加载、批量编码与向量写入，避免长期锁表中记录。
    store = None
    try:
        embedder = get_embedder()
        store = MilvusStore()
        # 检查／创建当前集合并核对维度，阻止不同编码配置写到不兼容的索引中。
        store.ensure()
        # 分批控制单次编码和写入规模；总文本快照仍在内存中，不是流式读取全文。
        size = get_settings().index_batch_size
        for start in range(0, len(rows), size):
            batch = rows[start : start + size]
            vectors = embedder.encode([content for _, content in batch])
            # 以 chunk_id 覆盖写入；任务重投可能重复编码，但不会为同一块新增重复主键。
            store.upsert(
                [
                    {
                        "chunk_id": chunk_id,
                        "version_id": version_id,
                        "document_id": document_id,
                        "knowledge_base_id": knowledge_base_id,
                        "vector": vector,
                    }
                    # strict=True 要求输入块与输出向量数量一致，避免静默丢失末尾数据。
                    for (chunk_id, _), vector in zip(batch, vectors, strict=True)
                ]
            )
        # 所有批次成功才报告 indexed；计数来自本次文本快照，并非向量库实时行数。
        status, error, count = "indexed", None, len(rows)
    except Exception:
        # 部分批次可能已写入，失败时不做跨存储回滚；SQL failed 状态会阻止这些向量被正常检索。
        logging.getLogger(__name__).exception("Index failed for version %s", version_id)
        status, error, count = "failed", INDEX_ERROR, 0
    # 释放向量连接后，再用新的短事务写最终状态；并非跨 MySQL 和 Milvus 的原子提交。
    finally:
        if store:
            store.close()

    # 第三阶段：新建短事务保存最终结果；写库异常会继续向上抛出，不伪报任务完成。
    with SessionLocal.begin() as db:
        job = _job(db, version_id)
        # 最终状态落库后，轮询接口才能看到成功数量或统一失败提示。
        job.status, job.error, job.chunks_indexed = status, error, count
    return {"status": status, "chunks": count}
