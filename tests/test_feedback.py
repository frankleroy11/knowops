"""Answer feedback: submission rules, tenant scoping and summary aggregation."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.db.deps import get_db
from app.db.session import Base
from app.main import app
from app.modules.auth import service
from app.modules.auth.models import ApiToken, KbMember, User
from app.modules.auth.security import hash_token
from app.modules.feedback.models import AnswerFeedback
from app.modules.knowledge.models import KnowledgeBase
from app.modules.tenant.models import Tenant

ENFORCED = Settings(auth_mode="enforced")
TOKENS = {"platform": "platform-token", "t1admin": "t1admin-token", "t1user": "t1user-token", "t2user": "t2user-token"}


def auth(name):
    return {"Authorization": f"Bearer {TOKENS[name]}"}


@pytest.fixture
def db_factory(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'feedback.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add_all([Tenant(id=1, name="默认租户", slug="default"), Tenant(id=2, name="Acme", slug="acme")])
        db.add_all([KnowledgeBase(id=1, name="IT-1", tenant_id=1), KnowledgeBase(id=2, name="IT-2", tenant_id=2)])
        db.add_all(
            [
                User(id=1, email="platform@corp", role="admin", tenant_id=None),
                User(id=2, email="t1admin@corp", role="admin", tenant_id=1),
                User(id=3, email="t1user@corp", role="viewer", tenant_id=1),
                User(id=4, email="t2user@corp", role="viewer", tenant_id=2),
            ]
        )
        db.add_all(
            [
                ApiToken(id=index, user_id=index, token_hash=hash_token(raw), label="")
                for index, raw in enumerate(TOKENS.values(), start=1)
            ]
        )
        db.add_all(
            [
                KbMember(id=1, kb_id=1, user_id=3, role="viewer"),
                KbMember(id=2, kb_id=2, user_id=4, role="viewer"),
            ]
        )
    return factory


@pytest.fixture
def client(db_factory):
    def database():
        with db_factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def enforced():
    with patch.object(service, "get_settings", return_value=ENFORCED):
        yield


def submit(client, name="t1user", rating="helpful", **extra):
    payload = {
        "rating": rating,
        "question": "VPN 怎么申请？",
        "answer": "先提交申请单。",
        "grounding_status": "quotes_validated",
        "citation_count": 1,
        "knowledge_base_id": 1,
        "scope": "knowledge_base",
    }
    payload.update(extra)
    return client.post("/api/v1/feedback", json=payload, headers=auth(name))


def test_viewer_feedback_is_recorded(client, enforced, db_factory):
    response = submit(client)
    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == "helpful" and body["tenant_id"] == 1 and body["user_id"] == 3
    with db_factory() as db:
        row = db.get(AnswerFeedback, body["id"])
        assert (row.knowledge_base_id, row.grounding_status, row.citation_count) == (1, "quotes_validated", 1)


def test_feedback_requires_authorized_knowledge_base(client, enforced):
    assert submit(client, knowledge_base_id=2).status_code == 404  # other tenant
    assert submit(client, name="t1admin", knowledge_base_id=2).status_code == 404
    assert submit(client, name="t1user", knowledge_base_id=1).status_code == 201


def test_same_tenant_non_member_is_forbidden(client, enforced, db_factory):
    with db_factory.begin() as db:
        db.add(User(id=9, email="t1other@corp", role="viewer", tenant_id=1))
        db.add(ApiToken(id=9, user_id=9, token_hash=hash_token("t1other-token"), label=""))
    response = client.post(
        "/api/v1/feedback",
        json={"rating": "helpful", "question": "q", "knowledge_base_id": 1},
        headers={"Authorization": "Bearer t1other-token"},
    )
    assert response.status_code == 403


def test_invalid_rating_is_rejected(client, enforced):
    assert submit(client, rating="maybe").status_code == 422


def test_scope_all_feedback_has_no_knowledge_base(client, enforced):
    body = submit(client, knowledge_base_id=None, scope="all").json()
    assert body["knowledge_base_id"] is None


def test_admin_list_is_tenant_scoped(client, enforced):
    submit(client, name="t1user", rating="helpful")
    submit(client, name="t2user", rating="not_helpful", knowledge_base_id=2)
    tenant_rows = client.get("/api/v1/admin/feedback", headers=auth("t1admin")).json()
    assert {(row["tenant_id"], row["rating"]) for row in tenant_rows} == {(1, "helpful")}
    every = client.get("/api/v1/admin/feedback", headers=auth("platform")).json()
    assert {row["tenant_id"] for row in every} == {1, 2}
    filtered = client.get("/api/v1/admin/feedback?rating=not_helpful", headers=auth("platform")).json()
    assert [row["rating"] for row in filtered] == ["not_helpful"]
    by_kb = client.get("/api/v1/admin/feedback?knowledge_base_id=1", headers=auth("platform")).json()
    assert [row["knowledge_base_id"] for row in by_kb] == [1]


def test_summary_aggregates_by_rating_and_grounding_status(client, enforced):
    submit(client, name="t1user", rating="helpful")
    submit(client, name="t1user", rating="helpful", grounding_status="model_refused")
    submit(client, name="t1user", rating="not_helpful", grounding_status="model_refused")
    summary = client.get("/api/v1/admin/feedback/summary", headers=auth("t1admin")).json()
    assert (summary["total"], summary["helpful"], summary["not_helpful"]) == (3, 2, 1)
    assert summary["helpful_rate"] == 0.6667
    assert summary["by_grounding_status"] == {"quotes_validated": 1, "model_refused": 2}


def test_feedback_reading_requires_admin(client, enforced):
    assert client.get("/api/v1/admin/feedback", headers=auth("t1user")).status_code == 403
    assert client.get("/api/v1/admin/feedback/summary", headers=auth("t1user")).status_code == 403


def test_feedback_submission_requires_authentication(client, enforced):
    assert client.post("/api/v1/feedback", json={"rating": "helpful", "question": "q"}).status_code == 401
