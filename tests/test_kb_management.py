from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker

from app.adapters.storage import LocalStorage
from app.adapters.vectorstore.milvus import collection_name
from app.core.config import Settings
from app.db.deps import get_db
from app.db.session import Base
from app.main import app
from app.modules.audit.models import AuditLog
from app.modules.auth import service
from app.modules.auth.deps import current_principal
from app.modules.auth.models import KbMember, User
from app.modules.auth.principal import Principal
from app.modules.feedback.models import AnswerFeedback
from app.modules.knowledge import management, router
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)
from app.modules.tenant.models import Tenant


@pytest.fixture
def env(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'kb.db'}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    with factory.begin() as db:
        db.add_all([Tenant(id=1, name="A", slug="a"), Tenant(id=2, name="B", slug="b")])
        db.flush()
        db.add(User(id=1, email="admin@a", role="admin", tenant_id=1))
        db.flush()
        db.add_all(
            [
                KnowledgeBase(id=1, name="delete-me", tenant_id=1),
                KnowledgeBase(id=2, name="other", tenant_id=2),
                KnowledgeBase(id=3, name="taken", tenant_id=1),
            ]
        )
        db.flush()
        for i in [1, 2]:
            db.add(Document(id=i, knowledge_base_id=i, filename=f"{i}.md"))
            db.flush()
            db.add(
                DocumentVersion(
                    id=i,
                    document_id=i,
                    version=1,
                    status="parsed",
                    content_hash=str(i) * 64,
                    storage_path=f"{i}.md",
                )
            )
            db.flush()
            db.add(Chunk(id=i, version_id=i, position=0, content="test"))
            db.add(
                VectorIndex(
                    version_id=i, collection=collection_name(), status="indexed", chunks_indexed=1
                )
            )
        db.add(KbMember(kb_id=1, user_id=1, role="owner"))
        db.add(AnswerFeedback(knowledge_base_id=1, tenant_id=1, question="q", rating="helpful"))
        db.add(
            AuditLog(tenant_id=1, action="historical", object_type="knowledge_base", object_id=1)
        )
    storage = LocalStorage(tmp_path)
    storage.directory.mkdir()
    for i in [1, 2]:
        storage.path(f"{i}.md").write_text("test")
    actor = [Principal(1, "admin@a", "admin", tenant_id=1)]

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[current_principal] = lambda: actor[0]
    store = MagicMock()
    try:
        with (
            patch.object(management, "MilvusStore", return_value=store),
            patch.object(router, "storage_backend", return_value=storage),
        ):
            yield factory, TestClient(app), actor, store, storage
    finally:
        app.dependency_overrides.clear()


def remove(client, name="delete-me"):
    return client.request("DELETE", "/api/v1/knowledge-bases/1", json={"confirm_name": name})


def test_delete_cascades_with_real_foreign_keys_and_retains_audit(env):
    factory, client, _, store, storage = env
    with factory.begin() as db:
        db.add(
            VectorIndex(
                version_id=1,
                collection="old_embedding_collection",
                status="indexed",
                chunks_indexed=1,
            )
        )
    result = remove(client)
    assert result.status_code == 200, result.text
    assert result.json()["chunks"] == 1
    assert not storage.path("1.md").exists()
    assert storage.path("2.md").exists()
    assert {call.args for call in store.delete_knowledge_base.call_args_list} == {
        (1, collection_name()),
        (1, "old_embedding_collection"),
    }
    with factory() as db:
        assert db.get(KnowledgeBase, 1) is None
        assert db.get(KnowledgeBase, 2) is not None
        assert db.get(DocumentVersion, 1) is None
        assert db.get(Chunk, 1) is None
        assert not list(db.scalars(select(KbMember)))
        assert not list(db.scalars(select(AnswerFeedback)))
        logs = list(db.scalars(select(AuditLog)))
        assert {log.action for log in logs} == {"historical", "kb.delete"}
        assert logs[-1].tenant_id == 1
    assert remove(client).status_code == 404


def test_confirmation_must_match_current_name(env):
    _, client, _, store, storage = env
    assert client.patch("/api/v1/knowledge-bases/1", json={"name": "new-name"}).status_code == 200
    assert remove(client).status_code == 409
    store.delete_knowledge_base.assert_not_called()
    assert storage.path("1.md").exists()
    assert remove(client, "new-name").status_code == 200


@pytest.mark.parametrize("role", ["viewer", "editor"])
def test_only_admin_can_rename_or_delete(env, role):
    factory, client, actor, store, _ = env
    actor[0] = Principal(1, "member@a", role, tenant_id=1)
    assert client.patch("/api/v1/knowledge-bases/1", json={"name": "bad"}).status_code == 403
    assert remove(client).status_code == 403
    store.delete_knowledge_base.assert_not_called()
    with factory() as db:
        assert db.get(KnowledgeBase, 1).name == "delete-me"


def test_other_tenant_admin_gets_404(env):
    _, client, actor, store, _ = env
    actor[0] = Principal(1, "admin@b", "admin", tenant_id=2)
    assert client.patch("/api/v1/knowledge-bases/1", json={"name": "bad"}).status_code == 404
    assert remove(client).status_code == 404
    store.delete_knowledge_base.assert_not_called()


def test_rename_conflict_and_blank_leave_original_name(env):
    factory, client, _, _, _ = env
    assert client.patch("/api/v1/knowledge-bases/1", json={"name": "taken"}).status_code == 409
    assert client.patch("/api/v1/knowledge-bases/1", json={"name": "  "}).status_code == 422
    with factory() as db:
        assert db.get(KnowledgeBase, 1).name == "delete-me"


@pytest.mark.parametrize("busy", ["pending", "indexing"])
def test_active_jobs_block_delete(env, busy):
    factory, client, _, store, _ = env
    with factory.begin() as db:
        if busy == "pending":
            db.get(DocumentVersion, 1).status = busy
        else:
            db.scalar(select(VectorIndex).where(VectorIndex.version_id == 1)).status = busy
    assert remove(client).status_code == 409
    store.delete_knowledge_base.assert_not_called()


def test_vector_failure_keeps_database_and_files(env):
    factory, client, _, store, storage = env
    store.delete_knowledge_base.side_effect = RuntimeError("private provider detail")
    response = remove(client)
    assert response.status_code == 503
    assert "private provider detail" not in response.text
    with factory() as db:
        assert db.get(KnowledgeBase, 1) is not None
        assert db.get(Chunk, 1) is not None
    assert storage.path("1.md").exists()
    store.delete_knowledge_base.side_effect = None
    assert remove(client).status_code == 200


def test_file_failure_reports_pending_and_gc_can_find_orphan(env):
    factory, client, _, _, storage = env
    with patch.object(storage, "delete", side_effect=OSError("unavailable")):
        response = remove(client)
    assert response.status_code == 200
    assert response.json()["file_cleanup_pending"] == 1
    with factory() as db:
        assert db.get(KnowledgeBase, 1) is None
    assert storage.path("1.md").exists()


def test_shared_upload_file_is_preserved(env):
    factory, client, _, _, storage = env
    with factory.begin() as db:
        db.get(DocumentVersion, 2).storage_path = "1.md"
    assert remove(client).status_code == 200
    assert storage.path("1.md").exists()


def test_unsafe_path_blocks_all_external_cleanup(env):
    factory, client, _, store, _ = env
    with factory.begin() as db:
        db.get(DocumentVersion, 1).storage_path = "../private.md"
    assert remove(client).status_code == 409
    store.delete_knowledge_base.assert_not_called()


def test_delete_requires_authentication(env):
    _, client, _, store, _ = env
    app.dependency_overrides.pop(current_principal)
    with patch.object(service, "get_settings", return_value=Settings(auth_mode="enforced")):
        assert remove(client).status_code == 401
    store.delete_knowledge_base.assert_not_called()
