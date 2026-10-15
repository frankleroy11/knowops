"""Answer feedback endpoints.

Any authenticated caller may rate an answer. Reading the collected feedback is an
administrator action and stays inside the caller's tenant, mirroring the audit
trail rules; the rows themselves are the record, so no duplicate audit entry is
written for every thumbs-up.
"""

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.db.deps import DB
from app.modules.auth import service as auth_service
from app.modules.auth.deps import AdminPrincipal, CurrentPrincipal
from app.modules.feedback.models import AnswerFeedback

router = APIRouter(tags=["答案反馈"])


class FeedbackIn(BaseModel):
    rating: Literal["helpful", "not_helpful"]
    question: str = Field(min_length=1, max_length=2000)
    answer: str = Field(default="", max_length=4000)
    reason: str = Field(default="", max_length=512)
    grounding_status: str = Field(default="", max_length=32)
    citation_count: int = Field(default=0, ge=0, le=100)
    scope: Literal["knowledge_base", "all"] = "knowledge_base"
    knowledge_base_id: int | None = Field(default=None, gt=0)


class FeedbackOut(BaseModel):
    id: int
    rating: str
    tenant_id: int | None
    user_id: int | None
    knowledge_base_id: int | None
    grounding_status: str
    citation_count: int
    question: str
    reason: str
    created_at: str | None


class FeedbackSummary(BaseModel):
    total: int
    helpful: int
    not_helpful: int
    helpful_rate: float | None
    by_grounding_status: dict[str, int]


def to_out(row: AnswerFeedback) -> FeedbackOut:
    return FeedbackOut(
        id=row.id,
        rating=row.rating,
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        knowledge_base_id=row.knowledge_base_id,
        grounding_status=row.grounding_status,
        citation_count=row.citation_count,
        question=row.question,
        reason=row.reason,
        created_at=row.created_at.isoformat() if row.created_at else None,
    )


def scope_for(db, principal) -> int | None:
    """Platform administrators see every tenant; tenant administrators their own."""
    if principal.is_platform_admin:
        return None
    return principal.tenant_id


@router.post("/feedback", response_model=FeedbackOut, status_code=201)
def submit_feedback(body: FeedbackIn, db: DB, principal: CurrentPrincipal):
    if body.knowledge_base_id is not None:
        # Reuse the authorization layer: rating an answer you cannot read is invalid.
        auth_service.require_kb(db, principal, body.knowledge_base_id, "read")
    row = AnswerFeedback(
        user_id=principal.id,
        tenant_id=principal.tenant_id,
        knowledge_base_id=body.knowledge_base_id,
        scope=body.scope,
        question=body.question.strip(),
        answer=body.answer.strip()[:4000],
        grounding_status=body.grounding_status,
        citation_count=body.citation_count,
        rating=body.rating,
        reason=body.reason.strip(),
    )
    db.add(row)
    db.commit()
    return to_out(row)


@router.get("/admin/feedback", response_model=list[FeedbackOut])
def list_feedback(
    db: DB,
    principal: AdminPrincipal,
    limit: int = 50,
    offset: int = 0,
    rating: Literal["helpful", "not_helpful"] | None = None,
    knowledge_base_id: int | None = None,
):
    tenant_id = scope_for(db, principal)
    query = select(AnswerFeedback).order_by(AnswerFeedback.id.desc())
    if tenant_id is not None:
        query = query.where(AnswerFeedback.tenant_id == tenant_id)
    if rating is not None:
        query = query.where(AnswerFeedback.rating == rating)
    if knowledge_base_id is not None:
        query = query.where(AnswerFeedback.knowledge_base_id == knowledge_base_id)
    rows = db.scalars(
        query.offset(max(0, offset)).limit(min(max(1, limit), 200))
    )
    return [to_out(row) for row in rows]


@router.get("/admin/feedback/summary", response_model=FeedbackSummary)
def feedback_summary(db: DB, principal: AdminPrincipal):
    tenant_id = scope_for(db, principal)
    conditions = [] if tenant_id is None else [AnswerFeedback.tenant_id == tenant_id]

    def count(*extra):
        return (
            db.scalar(
                select(func.count()).select_from(AnswerFeedback).where(*conditions, *extra)
            )
            or 0
        )

    total = count()
    helpful = count(AnswerFeedback.rating == "helpful")
    by_status = {
        status: digits
        for status, digits in db.execute(
            select(AnswerFeedback.grounding_status, func.count())
            .where(*conditions)
            .group_by(AnswerFeedback.grounding_status)
        ).all()
    }
    return FeedbackSummary(
        total=total,
        helpful=helpful,
        not_helpful=total - helpful,
        helpful_rate=round(helpful / total, 4) if total else None,
        by_grounding_status={key or "unknown": value for key, value in by_status.items()},
    )
