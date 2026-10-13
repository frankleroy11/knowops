from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.adapters.llm.qwen import LLMUnavailable, generate_grounded_answer
from app.modules.knowledge.router import DB
from app.modules.retrieval.router import Query, search

router = APIRouter(tags=["知识库问答"])
REFUSAL = "现有知识库资料不足，无法回答这个问题。"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    knowledge_base_id: int = Field(gt=0)
    top_k: int = Field(default=3, ge=1, le=8)


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
    result = search(
        Query(query=body.question, knowledge_base_id=body.knowledge_base_id, top_k=body.top_k), db
    )
    return answer_question(body, result["hits"])
