from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.adapters.vectorstore.milvus import collection_name
from app.db.session import Base
from app.main import app
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)
from app.modules.retrieval import service


@pytest.fixture
def sessions(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'index.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add(KnowledgeBase(id=1, name="test"))
        db.add(Document(id=1, knowledge_base_id=1, filename="vpn.md"))
        db.add(
            DocumentVersion(
                id=1,
                document_id=1,
                version=1,
                content_hash="a" * 64,
                storage_path="test.md",
                status="parsed",
            )
        )
        db.add(Chunk(id=1, version_id=1, position=0, content="连接 VPN"))
    return factory


def test_failed_index_retry_and_idempotent_keys(sessions):
    records = {}

    class Store:
        def ensure(self):
            pass

        def upsert(self, rows):
            records.update({r["chunk_id"]: r for r in rows})

        def close(self):
            pass

    class Embedder:
        def encode(self, texts):
            return [[1.0, 0.0] for _ in texts]

    with (
        patch.object(service, "SessionLocal", sessions),
        patch.object(service, "MilvusStore", Store),
    ):
        with patch.object(service, "get_embedder", side_effect=RuntimeError("private detail")):
            assert service.index_version(1)["status"] == "failed"
        with sessions() as db:
            job = db.scalar(select(VectorIndex))
            assert "private detail" not in job.error
            assert db.get(DocumentVersion, 1).status == "parsed"
        with patch.object(service, "get_embedder", return_value=Embedder()):
            assert service.index_version(1) == {"status": "indexed", "chunks": 1}
            assert service.index_version(1) == {"status": "indexed", "chunks": 1}
        assert len(records) == 1
        assert records[1]["knowledge_base_id"] == 1
        with sessions() as db:
            assert len(list(db.scalars(select(VectorIndex)))) == 1


def test_collection_changes_with_embedding_policy():
    from app.core.config import Settings

    with patch(
        "app.adapters.vectorstore.milvus.get_settings", return_value=Settings(embedding_dim=3)
    ):
        first = collection_name()
    with patch(
        "app.adapters.vectorstore.milvus.get_settings", return_value=Settings(embedding_dim=4)
    ):
        assert collection_name() != first


def test_search_requires_knowledge_base():
    response = TestClient(app).post("/api/v1/search", json={"query": "VPN"})
    assert response.status_code == 422


def test_search_resolves_custom_primary_key_and_filters_kb(sessions):
    from app.modules.knowledge.router import get_db
    from app.modules.retrieval import router as retrieval

    with sessions.begin() as db:
        db.add(
            VectorIndex(
                version_id=1, collection=collection_name(), status="indexed", chunks_indexed=1
            )
        )
        db.add(KnowledgeBase(id=2, name="other"))

    def database():
        with sessions() as db:
            yield db

    class Store:
        def search(self, vector, kb_id, limit):
            return [{"chunk_id": 1, "distance": 0.8}]

        def close(self):
            pass

    class Embedder:
        def encode(self, texts, **kwargs):
            return [[1.0, 0.0]]

    app.dependency_overrides[get_db] = database
    try:
        with (
            patch.object(retrieval, "MilvusStore", Store),
            patch.object(retrieval, "get_embedder", return_value=Embedder()),
        ):
            client = TestClient(app)
            response = client.post("/api/v1/search", json={"query": "VPN", "knowledge_base_id": 1})
            assert response.status_code == 200
            assert response.json()["hits"][0]["filename"] == "vpn.md"
            response = client.post("/api/v1/search", json={"query": "VPN", "knowledge_base_id": 2})
            assert response.json()["hits"] == []
    finally:
        app.dependency_overrides.clear()


def test_document_list_includes_independent_index_state(sessions):
    from app.modules.knowledge.router import documents

    with sessions.begin() as db:
        db.add(
            VectorIndex(
                version_id=1,
                collection=collection_name(),
                status="failed",
                chunks_indexed=0,
                error="索引暂不可用",
            )
        )
    with sessions() as db:
        rows = documents(1, db)
        assert rows[0]["status"] == "parsed"
        assert rows[0]["index_status"] == "failed"
        assert rows[0]["chunk_count"] == 1
        assert documents(1, db, offset=20) == []


def test_parse_task_dispatches_index_after_committed_parse():
    from app.workers.celery_app import index_document, ingest_document

    with (
        patch("app.modules.ingestion.service.process_version", return_value={"status": "parsed"}),
        patch.object(index_document, "delay") as queued,
    ):
        assert ingest_document.run(9)["index_queued"] is True
        queued.assert_called_once_with(9)
    with (
        patch("app.modules.ingestion.service.process_version", return_value={"status": "failed"}),
        patch.object(index_document, "delay") as queued,
    ):
        assert ingest_document.run(9)["status"] == "failed"
        queued.assert_not_called()


def test_broker_failure_keeps_parsed_result():
    from app.workers.celery_app import index_document, ingest_document

    with (
        patch("app.modules.ingestion.service.process_version", return_value={"status": "parsed"}),
        patch.object(index_document, "delay", side_effect=RuntimeError),
    ):
        result = ingest_document.run(9)
        assert result == {"status": "parsed", "index_queued": False}


def test_rerank_receives_only_authorized_candidates(sessions):
    from app.modules.knowledge.router import get_db
    from app.modules.retrieval import router as retrieval

    with sessions.begin() as db:
        db.add(
            VectorIndex(
                version_id=1, collection=collection_name(), status="indexed", chunks_indexed=1
            )
        )

    def database():
        with sessions() as db:
            yield db

    class Store:
        def search(self, vector, kb_id, limit):
            assert limit == 10
            return [{"chunk_id": 1, "distance": 0.9}, {"chunk_id": 9999, "distance": 0.8}]

        def close(self):
            pass

    class Embedder:
        def encode(self, texts, **kwargs):
            return [[1.0, 0.0]]

    def rerank(query, hits, top_k, max_per_document):
        assert len(hits) == 1
        assert hits[0]["chunk_id"] == 1
        return [{**hits[0], "rerank_score": 0.95}]

    app.dependency_overrides[get_db] = database
    try:
        with (
            patch.object(retrieval, "MilvusStore", Store),
            patch.object(retrieval, "get_embedder", return_value=Embedder()),
            patch("app.adapters.reranker.local.rerank_hits", side_effect=rerank),
        ):
            response = TestClient(app).post(
                "/api/v1/search",
                json={
                    "query": "VPN",
                    "knowledge_base_id": 1,
                    "rerank": True,
                    "candidate_k": 10,
                    "top_k": 3,
                },
            )
            assert response.status_code == 200
            assert response.json()["reranked"] is True
            assert response.json()["hits"][0]["score"] == 0.9
    finally:
        app.dependency_overrides.clear()
