"""真实 SQL/HTTP 授权链路，模型与 Redis 使用本地替身，不调用在线服务。"""

import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import sessionmaker

from app.adapters.vectorstore.milvus import collection_name
from app.core.config import get_settings
from app.db.deps import get_db
from app.db.session import Base
from app.main import app
from app.modules.auth.models import ApiToken, KbMember, User
from app.modules.auth.security import hash_token
from app.modules.chat import router as chat
from app.modules.faq import cache, service
from app.modules.faq import router as faq_router
from app.modules.faq.models import Faq
from app.modules.knowledge.models import (
    Chunk,
    Document,
    DocumentVersion,
    KnowledgeBase,
    VectorIndex,
)
from app.modules.tenant.models import Tenant


class MemoryRedis:
    def __init__(self):
        self.data = {}
        self.ttls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.data[key] = value
        self.ttls.append(ttl)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "auth_mode", "enforced")
    monkeypatch.setattr(settings, "faq_enabled", True)
    monkeypatch.setattr(settings, "answer_cache_enabled", True)
    engine = create_engine(f"sqlite:///{tmp_path / 'faq.db'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine)
    with factory.begin() as db:
        db.add_all([Tenant(id=1, name="A", slug="a"), Tenant(id=2, name="B", slug="b")])
        db.add_all(
            [
                User(id=1, email="admin@test", role="admin", tenant_id=1),
                User(id=2, email="viewer@test", role="viewer", tenant_id=1),
                User(id=3, email="other@test", role="admin", tenant_id=2),
            ]
        )
        db.add_all(
            [
                ApiToken(user_id=i, token_hash=hash_token(token))
                for i, token in enumerate(["admin", "viewer", "other"], 1)
            ]
        )
        db.add_all(
            [KnowledgeBase(id=1, name="A", tenant_id=1), KnowledgeBase(id=2, name="B", tenant_id=2)]
        )
        db.add(KbMember(kb_id=1, user_id=2, role="viewer"))
        db.add_all(
            [
                Document(id=1, knowledge_base_id=1, filename="policy.md"),
                Document(id=2, knowledge_base_id=2, filename="private.md"),
            ]
        )
        for i in [1, 2]:
            db.add(
                DocumentVersion(
                    id=i,
                    document_id=i,
                    storage_path=f"{i}.md",
                    content_hash="x",
                    status="parsed",
                    review_status="approved",
                    is_current=True,
                )
            )
            db.add(
                Chunk(id=i, version_id=i, position=0, content="午餐上限 128 元，必须提交电子发票。")
            )
            db.add(
                VectorIndex(
                    version_id=i, collection=collection_name(), status="indexed", chunks_indexed=1
                )
            )

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    encoder = Mock()
    encoder.encode.return_value = [[1.0, 0.0]]
    monkeypatch.setattr(faq_router, "get_embedder", lambda: encoder)
    monkeypatch.setattr(service, "get_embedder", lambda: encoder)
    redis = MemoryRedis()
    monkeypatch.setattr(cache, "client", lambda: redis)
    hit = {
        "chunk_id": 1,
        "version_id": 1,
        "document_id": 1,
        "knowledge_base_id": 1,
        "knowledge_base_name": "A",
        "filename": "policy.md",
        "position": 0,
        "content": "午餐上限 128 元，必须提交电子发票。",
    }
    search = Mock(return_value={"hits": [hit]})
    model = Mock(
        return_value={
            "answerable": True,
            "claims": [
                {
                    "text": "午餐上限 128 元。",
                    "evidence": [{"source_id": 1, "quote": "午餐上限 128 元"}],
                }
            ],
            "unanswered_questions": [],
        }
    )
    monkeypatch.setattr(chat, "search", search)
    monkeypatch.setattr(chat, "generate_grounded_answer", model)
    yield TestClient(app), factory, encoder, redis, search, model
    app.dependency_overrides.clear()
    engine.dispose()


def call(client, method, path, token="admin", **kwargs):
    return client.request(
        method, "/api/v1" + path, headers={"Authorization": "Bearer " + token}, **kwargs
    )


def create(client, **changes):
    body = {
        "knowledge_base_id": 1,
        "chunk_id": 1,
        "question": "午餐上限多少？",
        "answer": "午餐上限 128 元。",
        "quote": "午餐上限 128 元",
        "enabled": True,
    }
    body.update(changes)
    return call(client, "POST", "/admin/faqs", json=body)


def ask(client, question="午餐上限多少？", token="viewer", **changes):
    body = {"question": question, "scope": "all"}
    body.update(changes)
    return call(client, "POST", "/chat/ask", token=token, json=body)


def test_exact_faq_skips_embedding_search_and_llm(setup):
    client, _, encoder, _, search, model = setup
    assert create(client).status_code == 201
    encoder.reset_mock()
    response = ask(client)
    assert response.status_code == 200
    assert response.json()["faq_match"] == "exact"
    assert response.json()["answer_source"] == "faq"
    assert response.json()["citations"][0]["chunk_id"] == 1
    encoder.encode.assert_not_called()
    search.assert_not_called()
    model.assert_not_called()


@pytest.mark.parametrize("score,expected", [(0.84, "rag"), (0.86, "faq")])
def test_semantic_threshold(setup, score, expected):
    client, _, encoder, _, _, _ = setup
    create(client)
    encoder.encode.return_value = [[score, (1 - score**2) ** 0.5]]
    result = ask(client, "每人一天的午餐额度是多少？").json()
    assert result["answer_source"] == expected


def test_near_ties_and_conflicting_exact_answers_fall_back(setup):
    client, _, _, _, search, _ = setup
    create(client)
    create(client, question="每日报销上限？")
    assert ask(client, "午餐额度？").json()["answer_source"] == "rag"
    create(client, answer="另一个口径")
    assert ask(client).json()["answer_source"] == "rag"
    assert search.call_count == 2


@pytest.mark.parametrize(
    "field,value", [("is_current", False), ("review_status", "pending"), ("status", "failed")]
)
def test_stale_evidence_cannot_hit_faq(setup, field, value):
    client, factory, _, _, _, _ = setup
    create(client)
    with factory.begin() as db:
        setattr(db.get(DocumentVersion, 1), field, value)
    assert ask(client).json()["answer_source"] == "rag"


def test_cross_tenant_and_readonly_management_denied(setup):
    client, _, _, _, _, model = setup
    create(client)
    result = ask(client, token="other").json()
    assert result["answer_source"] == "rag"
    assert call(client, "POST", "/admin/faqs", token="viewer", json={}).status_code == 403
    assert call(client, "GET", "/admin/faqs?knowledge_base_id=1", token="other").status_code == 404
    assert (
        ask(client, token="other", scope="knowledge_base", knowledge_base_id=1).status_code == 404
    )
    assert model.call_count == 1  # 另一租户有其自己的已索引资料，FAQ 不会跨库命中。


def test_invalid_quote_or_wrong_source_rejected(setup):
    client, _, _, _, _, _ = setup
    assert create(client, quote="不存在的摘录").status_code == 422
    assert create(client, chunk_id=2).status_code == 422
    assert create(client, question="  ").status_code == 422


def test_rag_cache_hit_expiry_and_identity_separation(setup):
    client, _, _, redis, search, model = setup
    assert ask(client).json()["answer_source"] == "rag"
    assert ask(client).json()["answer_source"] == "cache"
    assert model.call_count == search.call_count == 1
    assert redis.ttls == [get_settings().answer_cache_ttl_seconds]
    # 同一问题的不同用户、检索参数必须使用不同键。
    assert ask(client, token="admin").json()["answer_source"] == "rag"
    assert ask(client, top_k=2).json()["answer_source"] == "rag"
    redis.data.clear()  # 模拟 TTL 到期。
    assert ask(client).json()["answer_source"] == "rag"
    assert model.call_count == 4


def test_permission_revocation_cannot_return_cached_answer(setup):
    client, factory, _, _, _, _ = setup
    ask(client)
    with factory.begin() as db:
        db.execute(delete(KbMember).where(KbMember.user_id == 2))
    assert ask(client, scope="knowledge_base", knowledge_base_id=1).status_code == 403
    assert ask(client).json()["answer_source"] != "cache"


def test_version_change_and_faq_edit_invalidate_cache(setup):
    client, factory, _, _, _, _ = setup
    ask(client)
    with factory.begin() as db:
        db.get(DocumentVersion, 1).is_current = False
    assert ask(client).json()["answer_source"] != "cache"
    with factory.begin() as db:
        db.get(DocumentVersion, 1).is_current = True
    row = create(client).json()
    assert ask(client).json()["answer_source"] == "faq"
    body = {
        k: row[k]
        for k in ["knowledge_base_id", "chunk_id", "question", "answer", "quote", "enabled"]
    }
    body["answer"] = "标准答案已更新：128 元。"
    assert call(client, "PUT", f"/admin/faqs/{row['id']}", json=body).status_code == 200
    assert ask(client).json()["answer"] == body["answer"]
    body["enabled"] = False
    call(client, "PUT", f"/admin/faqs/{row['id']}", json=body)
    assert ask(client).json()["answer_source"] == "rag"
    assert call(client, "DELETE", f"/admin/faqs/{row['id']}").status_code == 204
    with factory() as db:
        assert db.scalar(select(Faq)) is None


def test_redis_failure_and_corruption_fall_back(setup, monkeypatch):
    client, _, _, redis, _, model = setup
    ask(client)
    for key in redis.data:
        redis.data[key] = json.dumps({"answerable": True, "answer": "坏缓存"})
    assert ask(client).json()["answer_source"] == "rag"

    def unavailable():
        raise ConnectionError("offline")

    monkeypatch.setattr(cache, "client", unavailable)
    assert ask(client).json()["answer_source"] == "rag"
    assert model.call_count == 3


def test_refusal_is_not_cached(setup):
    client, _, _, redis, _, model = setup
    model.return_value = {"answerable": False, "claims": [], "unanswered_questions": ["资料缺失"]}
    assert not ask(client).json()["answerable"]
    assert not ask(client).json()["answerable"]
    assert not redis.data
    assert model.call_count == 2


@pytest.mark.parametrize(
    "left,right", [([], []), ([0, 0], [1, 0]), ([1], [1, 0]), ([float("nan")], [1]), (["bad"], [1])]
)
def test_invalid_vectors_never_match(left, right):
    assert service.cosine(left, right) == -1


def test_cached_citation_must_match_sql_body(setup):
    client, _, _, redis, _, model = setup
    ask(client)
    for key, value in redis.data.items():
        data = json.loads(value)
        data["citations"][0]["content"] = "伪造的午餐上限 128 元"
        redis.data[key] = json.dumps(data)
    assert ask(client).json()["answer_source"] == "rag"
    assert model.call_count == 2


def test_cached_claim_cannot_omit_evidence(setup):
    client, _, _, redis, _, _ = setup
    ask(client)
    for key, value in redis.data.items():
        data = json.loads(value)
        data["claims"] = []
        redis.data[key] = json.dumps(data)
    assert ask(client).json()["answer_source"] == "rag"


@pytest.mark.parametrize("target", ["retired", "index_failed"])
def test_retirement_and_index_failure_block_faq_and_cache(setup, target):
    client, factory, _, _, _, model = setup
    ask(client)
    create(client)
    with factory.begin() as db:
        if target == "retired":
            from datetime import datetime

            db.get(Document, 1).retired_at = datetime.now()
        else:
            db.scalar(select(VectorIndex).where(VectorIndex.version_id == 1)).status = "failed"
    result = ask(client).json()
    assert not result["answerable"] and result["answer_source"] == "rag"
    assert model.call_count == 1


def test_faq_switch_preserves_rag_path(setup, monkeypatch):
    client, _, _, _, _, model = setup
    create(client)
    monkeypatch.setattr(get_settings(), "faq_enabled", False)
    assert ask(client).json()["answer_source"] == "rag"
    assert model.call_count == 1


def test_disable_unchanged_faq_without_model_service(setup):
    client, _, encoder, _, _, _ = setup
    row = create(client).json()
    body = {
        k: row[k]
        for k in ["knowledge_base_id", "chunk_id", "question", "answer", "quote", "enabled"]
    }
    body["enabled"] = False
    encoder.encode.side_effect = RuntimeError("offline")
    response = call(client, "PUT", f"/admin/faqs/{row['id']}", json=body)
    assert response.status_code == 200
    assert response.json()["enabled"] is False
