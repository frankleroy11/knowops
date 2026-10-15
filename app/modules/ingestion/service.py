from sqlalchemy import delete, select

from app.adapters.storage import LocalStorage
from app.core.config import ROOT
from app.db.session import SessionLocal
from app.modules.ingestion.parser import parse_chunks
from app.modules.knowledge.models import Chunk, DocumentVersion


def process_version(version_id: int):
    # Lock the version for the transaction: duplicate deliveries serialize.
    # This first implementation suits bounded local files; large files need leases/staged batches.
    with SessionLocal.begin() as db:
        version = db.scalar(
            select(DocumentVersion).where(DocumentVersion.id == version_id).with_for_update()
        )
        if version is None:
            return {"status": "missing"}
        if version.status == "parsed":
            return {"status": "parsed", "duplicate": True}
        try:
            chunks = parse_chunks(
                LocalStorage(ROOT).path(version.storage_path),
                size=version.chunk_size,
                overlap=version.chunk_overlap,
                strategy=version.chunk_strategy,
            )
        except Exception:  # noqa: BLE001 - isolate malformed input, expose no private exception text
            version.status = "failed"
            version.error = "解析失败：请检查 UTF-8 编码、PDF 是否加密或为扫描件"
            return {"status": "failed"}
        db.execute(delete(Chunk).where(Chunk.version_id == version_id))
        db.add_all(Chunk(version_id=version_id, **chunk) for chunk in chunks)
        version.status = "parsed"
        version.error = None
        return {"status": "parsed", "chunks": len(chunks)}
