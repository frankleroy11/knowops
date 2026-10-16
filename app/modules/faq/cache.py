"""Redis 精确请求缓存；Redis 故障或非法内容均降级为未命中，不缓存拒答和错误。"""

import json

from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.knowledge.models import Chunk, Document, DocumentVersion


def client():
    return Redis.from_url(
        get_settings().redis_url,
        decode_responses=True,
        socket_connect_timeout=0.3,
        socket_timeout=0.3,
    )


def read(key, state, db):
    if not get_settings().answer_cache_enabled:
        return None
    try:
        with client() as redis:
            raw = redis.get(key)
        data = json.loads(raw) if raw else None
        if not isinstance(data, dict) or data.get("answerable") is not True:
            return None
        if data.get("grounding_status") != "quotes_validated" or not isinstance(
            data.get("answer"), str
        ):
            return None
        citations = data.get("citations")
        if (
            not isinstance(citations, list)
            or not citations
            or not isinstance(data.get("claims"), list)
        ):
            return None
        if not all(
            c["version_id"] in state["version_ids"] and c["knowledge_base_id"] in state["kb_ids"]
            for c in citations
        ):
            return None
        # 缓存只是优化，返回前仍核对当前 SQL 正文和引用，不能信任缓存中的来源字段。
        from app.modules.chat.router import Claim, normalize_quote

        claims = [Claim.model_validate(claim) for claim in data["claims"]]
        if not claims or data["answer"] != "\n".join(c.text for c in claims):
            return None
        by_source = {c["source_id"]: c for c in citations}
        if len(by_source) != len(citations):
            return None
        rows = db.execute(
            select(Chunk, Document)
            .join(DocumentVersion, Chunk.version_id == DocumentVersion.id)
            .join(Document, DocumentVersion.document_id == Document.id)
            .where(
                Chunk.id.in_([c["chunk_id"] for c in citations]),
                Chunk.version_id.in_(state["version_ids"]),
                Document.knowledge_base_id.in_(state["kb_ids"]),
            )
        ).all()
        actual = {chunk.id: (chunk, doc) for chunk, doc in rows}
        for citation in citations:
            chunk, doc = actual[citation["chunk_id"]]
            if (
                citation["content"] != chunk.content
                or citation["version_id"] != chunk.version_id
                or citation["document_id"] != doc.id
                or citation["knowledge_base_id"] != doc.knowledge_base_id
            ):
                return None
        for claim in claims:
            for evidence in claim.evidence:
                source = by_source.get(evidence.source_id)
                if (
                    source is None
                    or not normalize_quote(evidence.quote)
                    or normalize_quote(evidence.quote)
                    not in normalize_quote(source["content"][:1200])
                ):
                    return None
        return data
    except (RedisError, ValueError, TypeError, KeyError):
        return None


def write(key, answer):
    s = get_settings()
    if (
        not s.answer_cache_enabled
        or not answer.get("answerable")
        or answer.get("grounding_status") != "quotes_validated"
    ):
        return
    try:
        with client() as redis:
            redis.setex(key, s.answer_cache_ttl_seconds, json.dumps(answer, ensure_ascii=False))
    except (RedisError, ValueError, TypeError):
        pass
