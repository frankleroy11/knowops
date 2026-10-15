from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.modules.auth.principal import Principal
from app.modules.feedback.models import AnswerFeedback
from app.modules.knowledge import operations
from app.modules.knowledge.models import Chunk, Document, DocumentVersion, VectorIndex
from tests.test_kb_management import env as kb_env


@pytest.fixture
def env(tmp_path):
    yield from kb_env.__wrapped__(tmp_path)


def test_document_delete_preserves_kb_neighbors_and_audit(env):
    factory, client, _, _, storage = env
    vectors = MagicMock()
    with patch.object(operations, "MilvusStore", return_value=vectors):
        response = client.request(
            "DELETE", "/api/v1/documents/1", json={"confirm_filename": "1.md"}
        )
    assert response.status_code == 200, response.text
    assert response.json()["chunks"] == 1
    vectors.delete_document.assert_called_once()
    with factory() as db:
        assert db.get(Document, 1) is None
        assert db.get(DocumentVersion, 1) is None
        assert db.get(Chunk, 1) is None
        assert db.get(Document, 2) is not None
        assert db.scalar(select(AnswerFeedback)) is not None
    assert not storage.path("1.md").exists()
    assert storage.path("2.md").exists()


@pytest.mark.parametrize(
    "principal,status",
    [
        (Principal(1, "viewer", "viewer", tenant_id=1), 403),
        (Principal(1, "other", "admin", tenant_id=2), 404),
    ],
)
def test_document_delete_acl(env, principal, status):
    _, client, actor, _, _ = env
    actor[0] = principal
    assert (
        client.request(
            "DELETE", "/api/v1/documents/1", json={"confirm_filename": "1.md"}
        ).status_code
        == status
    )


def test_document_delete_confirmation_busy_and_vector_failure(env):
    factory, client, _, _, storage = env
    url = "/api/v1/documents/1"
    with patch.object(operations, "MilvusStore") as store:
        assert client.request("DELETE", url, json={"confirm_filename": "wrong"}).status_code == 409
        store.assert_not_called()
        with factory.begin() as db:
            db.get(DocumentVersion, 1).status = "pending"
        assert client.request("DELETE", url, json={"confirm_filename": "1.md"}).status_code == 409
        store.assert_not_called()
        with factory.begin() as db:
            db.get(DocumentVersion, 1).status = "parsed"
        store.return_value.delete_document.side_effect = RuntimeError("secret")
        response = client.request("DELETE", url, json={"confirm_filename": "1.md"})
        assert response.status_code == 503
        assert "secret" not in response.text
        assert storage.path("1.md").exists()
        with factory() as db:
            assert db.get(Document, 1) is not None


def test_failure_list_scoped_to_tenant(env):
    factory, client, actor, _, _ = env
    with factory.begin() as db:
        db.get(DocumentVersion, 1).status = "failed"
        db.get(DocumentVersion, 2).status = "failed"
    rows = client.get("/api/v1/admin/document-failures").json()
    assert [r["version_id"] for r in rows] == [1]
    assert rows[0]["stage"] == "parse"
    assert "storage_path" not in rows[0]
    actor[0] = Principal(1, "viewer", "viewer", tenant_id=1)
    assert client.get("/api/v1/admin/document-failures").status_code == 403


def test_retry_dispatch_failure_stays_retryable_and_success_blocks_duplicate(env):
    factory, client, _, _, _ = env
    with factory.begin() as db:
        db.get(DocumentVersion, 1).status = "failed"
    url = "/api/v1/document-versions/1/retry"
    with patch(
        "app.modules.knowledge.router.ingest_document.delay", side_effect=RuntimeError("secret")
    ):
        assert client.post(url).status_code == 503
    with factory() as db:
        assert db.get(DocumentVersion, 1).status == "failed"
    with patch("app.modules.knowledge.router.ingest_document.delay") as task:
        task.return_value.id = "test-task"
        assert client.post(url).status_code == 202
        assert client.post(url).status_code == 409
        task.assert_called_once()


def test_versions_publish_approved_ready_only(env):
    factory, client, _, _, _ = env
    with factory.begin() as db:
        db.add(
            DocumentVersion(
                id=10,
                document_id=1,
                version=2,
                content_hash="b" * 64,
                storage_path="new.md",
                status="parsed",
                is_current=False,
                review_status="pending",
            )
        )
    assert len(client.get("/api/v1/documents/1/versions").json()) == 2
    assert client.post("/api/v1/document-versions/10/publish").status_code == 409
    with factory.begin() as db:
        db.get(DocumentVersion, 10).review_status = "approved"
        db.add(
            VectorIndex(
                version_id=10,
                collection=operations.collection_name(),
                status="indexed",
                chunks_indexed=1,
            )
        )
    assert client.post("/api/v1/document-versions/10/publish").status_code == 200
    with factory() as db:
        assert db.get(DocumentVersion, 10).is_current
        assert not db.get(DocumentVersion, 1).is_current
    assert client.post("/api/v1/document-versions/1/publish").status_code == 200


def test_retry_index_failure_and_duplicate_guard(env):
    factory, client, _, _, _ = env
    with factory.begin() as db:
        db.scalar(select(VectorIndex).where(VectorIndex.version_id == 1)).status = "failed"
    url = "/api/v1/document-versions/1/index"
    with patch("app.workers.celery_app.index_document.delay", side_effect=RuntimeError("secret")):
        assert client.post(url).status_code == 503
    with factory() as db:
        assert db.scalar(select(VectorIndex).where(VectorIndex.version_id == 1)).status == "failed"
    with patch("app.workers.celery_app.index_document.delay") as task:
        task.return_value.id = "test-index"
        assert client.post(url).status_code == 202
        assert client.post(url).status_code == 409
        task.assert_called_once()


def test_search_filters_published_versions_before_vector_candidates(env):
    from app.modules.retrieval import router as retrieval

    factory, client, _, _, _ = env
    with factory.begin() as db:
        db.add(
            DocumentVersion(
                id=10,
                document_id=1,
                version=2,
                content_hash="b" * 64,
                storage_path="new.md",
                status="parsed",
                is_current=False,
            )
        )
        db.add(
            VectorIndex(version_id=10, collection=operations.collection_name(), status="indexed")
        )
    with (
        patch.object(retrieval, "MilvusStore") as store,
        patch.object(retrieval, "get_embedder") as embedding,
    ):
        embedding.return_value.encode.return_value = [[1.0]]
        store.return_value.search.return_value = [{"chunk_id": 1, "distance": 0.9}]
        response = client.post("/api/v1/search", json={"query": "test", "knowledge_base_id": 1})
        assert response.status_code == 200
        assert response.json()["hits"][0]["version_id"] == 1
        assert store.return_value.search.call_args.kwargs["version_ids"] == [1]
