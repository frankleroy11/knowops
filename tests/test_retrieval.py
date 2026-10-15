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


def test_indexing_commits_progress_before_embedding(sessions):
    """During the embedding call another session must already see status="indexing".

    The previous implementation kept one transaction (with FOR UPDATE) open across the
    embedding call, so no other session could observe the row or write to the version.
    """
    from app.modules.retrieval import service

    observed = {}

    class Embedder:
        def encode(self, texts):
            with sessions() as db:
                job = db.scalar(select(VectorIndex))
                observed["status"] = job.status if job else None
            return [[1.0, 0.0] for _ in texts]

    class Store:
        def ensure(self):
            pass

        def upsert(self, rows):
            pass

        def close(self):
            pass

    with (
        patch.object(service, "SessionLocal", sessions),
        patch.object(service, "MilvusStore", Store),
        patch.object(service, "get_embedder", return_value=Embedder()),
    ):
        assert service.index_version(1) == {"status": "indexed", "chunks": 1}
    assert observed["status"] == "indexing"
    with sessions() as db:
        assert db.scalar(select(VectorIndex)).status == "indexed"


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
        def search(self, vector, kb_id, limit, **kwargs):
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
        def search(self, vector, kb_id, limit, **kwargs):
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


def test_all_scope_resolves_existing_kbs_and_preserves_single_kb_filter(sessions):
    from app.modules.knowledge.router import get_db
    from app.modules.retrieval import router as retrieval

    with sessions.begin() as db:
        db.add(KnowledgeBase(id=2, name="人事"))
        db.add(Document(id=2, knowledge_base_id=2, filename="leave.md"))
        db.add(
            DocumentVersion(
                id=2,
                document_id=2,
                version=1,
                content_hash="b" * 64,
                storage_path="leave.md",
                status="parsed",
            )
        )
        db.add(Chunk(id=2, version_id=2, position=0, content="年假5天"))
        for version in [1, 2]:
            db.add(
                VectorIndex(
                    version_id=version,
                    collection=collection_name(),
                    status="indexed",
                    chunks_indexed=1,
                )
            )

    def database():
        with sessions() as db:
            yield db

    class Store:
        def search(self, vector, kb_id, limit, **kwargs):
            assert kb_id == [1, 2] or kb_id == 1
            return [
                {"chunk_id": 1, "distance": 0.9},
                {"chunk_id": 2, "distance": 0.8},
                {"chunk_id": 9999, "distance": 0.7},
            ]

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
            result = client.post(
                "/api/v1/search", json={"query": "VPN和年假", "scope": "all"}
            ).json()
            assert result["scope"] == "all"
            assert [(h["knowledge_base_id"], h["knowledge_base_name"]) for h in result["hits"]] == [
                (1, "test"),
                (2, "人事"),
            ]
            result = client.post(
                "/api/v1/search", json={"query": "VPN", "knowledge_base_id": 1}
            ).json()
            assert [h["chunk_id"] for h in result["hits"]] == [1]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.parametrize("path", ["/api/v1/search", "/api/v1/chat/ask"])
@pytest.mark.parametrize(
    "scope",
    [
        {"scope": "all", "knowledge_base_id": 1},
        {"scope": "invalid"},
        {"scope": "knowledge_base"},
        {"knowledge_base_id": 0},
    ],
)
def test_scope_is_explicit_and_unambiguous(path, scope):
    response = TestClient(app).post(path, json={"query": "VPN", "question": "VPN", **scope})
    assert response.status_code == 422


def test_unified_ask_passes_explicit_scope():
    from app.modules.chat import router as chat
    from app.modules.knowledge.router import get_db

    app.dependency_overrides[get_db] = lambda: None
    try:
        with patch.object(chat, "search", return_value={"hits": []}) as search:
            response = TestClient(app).post(
                "/api/v1/chat/ask", json={"question": "VPN", "scope": "all"}
            )
            assert response.status_code == 200
            assert not response.json()["answerable"]
            assert search.call_args.args[0].scope == "all"
            assert search.call_args.args[0].knowledge_base_id is None
    finally:
        app.dependency_overrides.clear()


def test_global_vector_search_has_explicit_numeric_filter():
    from unittest.mock import MagicMock

    from app.adapters.vectorstore.milvus import MilvusStore

    store = object.__new__(MilvusStore)
    store.name = "test"
    store.client = MagicMock()
    store.client.search.return_value = [[]]
    assert store.search([1.0, 0.0], [2, 5], 3) == []
    assert store.client.search.call_args.kwargs["filter"] == "knowledge_base_id in [2,5]"
    store.client.search.reset_mock()
    assert store.search([1.0, 0.0], [], 3) == []
    store.client.search.assert_not_called()


def test_empty_all_scope_never_issues_unfiltered_vector_search():
    from unittest.mock import MagicMock

    from app.modules.retrieval import router as retrieval

    db = MagicMock()
    db.scalars.return_value = []
    with (
        patch.object(retrieval, "MilvusStore") as store,
        patch.object(retrieval, "get_embedder") as embedder,
    ):
        result = retrieval.search(retrieval.Query(query="VPN", scope="all"), db)
    assert result["hits"] == []
    store.assert_not_called()
    embedder.assert_not_called()


def test_neighbors_stay_in_same_version_document_and_kb(sessions):
    from app.modules.retrieval.context import expand_neighbors

    with sessions.begin() as db:
        db.add(Chunk(id=2, version_id=1, position=1, content="相邻表格"))
        db.add(Chunk(id=3, version_id=1, position=2, content="距离两片，不补全"))
        db.add(
            VectorIndex(
                version_id=1, collection=collection_name(), status="indexed", chunks_indexed=3
            )
        )
        db.add(KnowledgeBase(id=2, name="other"))
        db.add(Document(id=2, knowledge_base_id=2, filename="other.md"))
        db.add(
            DocumentVersion(
                id=2,
                document_id=2,
                version=1,
                content_hash="b" * 64,
                storage_path="other.md",
                status="parsed",
            )
        )
        db.add(Chunk(id=4, version_id=2, position=1, content="其他库，不补全"))
        db.add(
            VectorIndex(
                version_id=2, collection=collection_name(), status="indexed", chunks_indexed=1
            )
        )
    anchors = [
        {
            "chunk_id": 1,
            "version_id": 1,
            "document_id": 1,
            "knowledge_base_id": 1,
            "position": 0,
            "content": "连接VPN",
            "score": 0.9,
        }
    ]
    with sessions() as db:
        result = expand_neighbors(anchors, db)
    assert [h["chunk_id"] for h in result] == [1, 2]
    assert result[1]["knowledge_base_id"] == 1
    assert result[1]["filename"] == "vpn.md"
    assert result[1]["context_role"] == "neighbor"
    assert "score" not in result[1]
    assert "context_role" not in anchors[0]


def test_neighbor_budget_keeps_all_anchors_first(sessions):
    from app.modules.retrieval.context import expand_neighbors

    with sessions.begin() as db:
        db.add(
            VectorIndex(
                version_id=1, collection=collection_name(), status="indexed", chunks_indexed=11
            )
        )
        for position in range(1, 11):
            db.add(
                Chunk(id=position + 1, version_id=1, position=position, content=f"片段{position}")
            )
    anchors = [
        {
            "chunk_id": p + 1,
            "version_id": 1,
            "document_id": 1,
            "knowledge_base_id": 1,
            "position": p,
            "content": f"片段{p}",
        }
        for p in [0, 2, 4, 6, 8]
    ]
    with sessions() as db:
        result = expand_neighbors(anchors, db)
    assert len(result) == 8
    assert [h["chunk_id"] for h in result[:5]] == [1, 3, 5, 7, 9]
    assert len({h["chunk_id"] for h in result}) == 8


def test_unindexed_neighbors_are_not_added(sessions):
    from app.modules.retrieval.context import expand_neighbors

    with sessions.begin() as db:
        db.add(Chunk(id=2, version_id=1, position=1, content="没有索引"))
    anchors = [
        {
            "chunk_id": 1,
            "version_id": 1,
            "document_id": 1,
            "knowledge_base_id": 1,
            "position": 0,
            "content": "连接VPN",
        }
    ]
    with sessions() as db:
        assert len(expand_neighbors(anchors, db)) == 1


def test_empty_context_does_not_query_database():
    from unittest.mock import MagicMock

    from app.modules.retrieval.context import expand_neighbors

    db = MagicMock()
    assert expand_neighbors([], db) == []
    db.execute.assert_not_called()
