# 中文导读：
# 统一问答链路：授权检索、可选相邻块扩展、模型生成、逐条引用校验
# 证据不足或输出无法校验时拒答；原文匹配本身不证明语义支持

from time import perf_counter
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.adapters.llm.qwen import LLMUnavailable, generate_grounded_answer
from app.core.config import get_settings
from app.db.deps import DB
from app.modules.auth.deps import CurrentPrincipal
from app.modules.faq import cache as answer_cache
from app.modules.faq import service as faq_service
from app.modules.retrieval.context import MAX_CONTEXT_CHUNKS, expand_neighbors
from app.modules.retrieval.router import Query, search

router = APIRouter(tags=["知识库问答"])
REFUSAL = "现有知识库资料不足，无法回答这个问题。"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    knowledge_base_id: int | None = Field(default=None, gt=0)
    scope: Literal["knowledge_base", "all"] = "knowledge_base"
    top_k: int = Field(default=3, ge=1, le=8)
    expand_context: bool = False
    rerank: bool = False
    candidate_k: int = Field(default=10, ge=1, le=50)
    max_per_document: int = Field(default=0, ge=0, le=50)

    @model_validator(mode="after")
    def validate_retrieval(self):
        Query(
            query=self.question,
            knowledge_base_id=self.knowledge_base_id,
            scope=self.scope,
            top_k=self.top_k,
            rerank=self.rerank,
            candidate_k=self.candidate_k,
            max_per_document=self.max_per_document,
        )
        return self


class Evidence(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    source_id: int
    quote: str = Field(min_length=1, max_length=1200)


class Claim(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    text: str = Field(min_length=1, max_length=2000)
    evidence: list[Evidence] = Field(min_length=1, max_length=8)


class ModelAnswer(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    answerable: bool
    claims: list[Claim] = Field(max_length=20)
    unanswered_questions: list[str] = Field(max_length=20)


# 统一构造拒答结果，让前端能够区分证据不足与正常回答。
def refuse(reason):
    return {
        "answer": REFUSAL,
        "answerable": False,
        "citations": [],
        "claims": [],
        "grounding_status": reason,
    }


# 统一摘录格式用于原文匹配；这一步只核验文本存在，不判断结论是否被语义支持。
def normalize_quote(text):
    # Permit whitespace layout differences only, not fuzzy matches or omitted words.
    return " ".join(text.split())


# 将召回证据交给模型后逐条验证来源与摘录；任一必要校验失败时走拒答路径。
def answer_question(body: AskRequest, hits: list[dict]):
    selected = hits[: MAX_CONTEXT_CHUNKS if body.expand_context else body.top_k]
    sources = [
        {
            "id": i,
            "filename": h.get("filename", ""),
            "knowledge_base": h.get("knowledge_base_name", ""),
            "content": h["content"][:1200],
        }
        for i, h in enumerate(selected, 1)
    ]
    if not sources:
        return refuse("no_context")
    try:
        generated = ModelAnswer.model_validate(generate_grounded_answer(body.question, sources))
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    except ValidationError:
        raise HTTPException(502, "模型响应格式不符合要求，请重试") from None
    if not generated.answerable:
        return refuse("model_refused")
    if generated.unanswered_questions:
        return refuse("incomplete_answer")
    if not generated.claims:
        return refuse("missing_claims")
    ids, claims, corrections = [], [], []
    for claim_index, claim in enumerate(generated.claims):
        if not claim.text.strip():
            return refuse("invalid_evidence")
        evidence = []
        for item in claim.evidence:
            quote = normalize_quote(item.quote)
            if not quote:
                return refuse("invalid_evidence")
            source_id = item.source_id
            valid_id = 1 <= source_id <= len(sources)
            if not valid_id or quote not in normalize_quote(sources[source_id - 1]["content"]):
                # Recover only from a unique exact quote in the actual bounded context.
                # Never search other documents, infer an ID, or accept fuzzy evidence.
                matches = [
                    source["id"]
                    for source in sources
                    if quote in normalize_quote(source["content"])
                ]
                if len(matches) != 1:
                    return refuse("invalid_source" if not valid_id else "invalid_evidence")
                source_id = matches[0]
                corrections.append(
                    {
                        "claim_index": claim_index,
                        "model_source_id": item.source_id,
                        "source_id": source_id,
                    }
                )
            if source_id not in ids:
                ids.append(source_id)
            evidence.append({"source_id": source_id, "quote": item.quote})
        claims.append({"text": claim.text.strip(), "evidence": evidence})
    return {
        "answer": "\n".join(c["text"] for c in claims),
        "answerable": True,
        "claims": claims,
        "source_id_corrections": corrections,
        "grounding_status": "quotes_validated",
        "citations": [{"source_id": i, **selected[i - 1]} for i in ids],
    }


@router.post("/chat/ask")
def ask(body: AskRequest, db: DB, principal: CurrentPrincipal):
    if not body.question.strip():
        raise HTTPException(422, "问题不能为空")
    started = perf_counter()
    settings = get_settings()
    state = None
    if settings.faq_enabled or settings.answer_cache_enabled:
        state = faq_service.context(db, principal, body)
        if not state["version_ids"]:
            answer = refuse("no_context")
            answer.update(
                answer_source="rag",
                cache_hit=False,
                context_chunk_count=0,
                context_expanded=body.expand_context,
            )
            answer["timings_ms"] = {
                "retrieval": round((perf_counter() - started) * 1000, 2),
                "generation": 0,
                "total": round((perf_counter() - started) * 1000, 2),
            }
            return answer
        faq = faq_service.match(body.question, state)
        if faq:
            faq["cache_hit"] = False
            faq["timings_ms"] = {
                "retrieval": 0,
                "generation": 0,
                "total": round((perf_counter() - started) * 1000, 2),
            }
            return faq
        cached = answer_cache.read(state["cache_key"], state, db)
        if cached:
            cached["answer_source"] = "cache"
            cached["cache_hit"] = True
            cached["timings_ms"] = {
                "retrieval": 0,
                "generation": 0,
                "total": round((perf_counter() - started) * 1000, 2),
            }
            return cached
    result = search(
        Query(
            query=body.question,
            knowledge_base_id=body.knowledge_base_id,
            scope=body.scope,
            top_k=body.top_k,
            rerank=body.rerank,
            candidate_k=body.candidate_k,
            max_per_document=body.max_per_document,
        ),
        db,
        principal,
    )
    hits = expand_neighbors(result["hits"], db) if body.expand_context else result["hits"]
    retrieved = perf_counter()
    answer = answer_question(body, hits)
    finished = perf_counter()
    answer["context_chunk_count"] = len(hits)
    answer["context_expanded"] = body.expand_context
    answer["timings_ms"] = {
        "retrieval": round((retrieved - started) * 1000, 2),
        "generation": round((finished - retrieved) * 1000, 2),
        "total": round((finished - started) * 1000, 2),
    }
    answer["answer_source"] = "rag"
    answer["cache_hit"] = False
    if state is not None:
        answer_cache.write(state["cache_key"], answer)
    return answer
