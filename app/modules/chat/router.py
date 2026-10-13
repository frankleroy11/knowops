from time import perf_counter
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.adapters.llm.qwen import LLMUnavailable, generate_grounded_answer
from app.modules.knowledge.router import DB
from app.modules.retrieval.router import Query, search

router = APIRouter(tags=["知识库问答"])
REFUSAL = "现有知识库资料不足，无法回答这个问题。"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    knowledge_base_id: int | None = Field(default=None, gt=0)
    scope: Literal["knowledge_base", "all"] = "knowledge_base"
    top_k: int = Field(default=3, ge=1, le=8)
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


class ModelAnswer(BaseModel):
    model_config = ConfigDict(strict=True)
    answer: str = Field(min_length=1, max_length=10000)
    source_ids: list[int]
    answerable: bool


def answer_question(body: AskRequest, hits: list[dict]):
    # Cap context size; local character chunks are at most 800 characters each.
    selected = hits[: body.top_k]
    sources = [{"id": i, "content": h["content"][:1200]} for i, h in enumerate(selected, 1)]
    if not sources:
        return {"answer": REFUSAL, "answerable": False, "citations": []}
    try:
        generated = ModelAnswer.model_validate(generate_grounded_answer(body.question, sources))
    except LLMUnavailable as exc:
        raise HTTPException(503, str(exc)) from None
    except ValidationError:
        raise HTTPException(502, "模型响应格式不符合要求，请重试") from None
    ids = list(dict.fromkeys(generated.source_ids))
    # Reject unsupported IDs rather than silently attaching unrelated sources.
    if not generated.answerable or not ids or any(i < 1 or i > len(selected) for i in ids):
        return {"answer": REFUSAL, "answerable": False, "citations": []}
    return {
        "answer": generated.answer,
        "answerable": True,
        "citations": [{"source_id": i, **selected[i - 1]} for i in ids],
    }


@router.post("/chat/ask")
def ask(body: AskRequest, db: DB):
    if not body.question.strip():
        raise HTTPException(422, "问题不能为空")
    started = perf_counter()
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
    )
    retrieved = perf_counter()
    answer = answer_question(body, result["hits"])
    finished = perf_counter()
    answer["timings_ms"] = {
        "retrieval": round((retrieved - started) * 1000, 2),
        "generation": round((finished - retrieved) * 1000, 2),
        "total": round((finished - started) * 1000, 2),
    }
    return answer
