# 中文导读：
# 问答反馈快照：保留提问、回答与证据上下文，便于后续复盘
# 快照不依赖被引用文档持续存在

"""Answer feedback: the online half of the evaluation loop.

Scripted evaluations (`evals/`, `scripts/evaluate_*.py`) measure retrieval and
grounding offline. This table captures what real users think of a specific answer,
including the `grounding_status` and citation count that produced it, so a
regression in generation quality becomes visible without a manual test run.
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base

RATINGS = ("helpful", "not_helpful")


class AnswerFeedback(Base):
    __tablename__ = "answer_feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    tenant_id: Mapped[int | None] = mapped_column(
        ForeignKey("tenants.id"), nullable=True, index=True
    )
    knowledge_base_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_bases.id"), nullable=True, index=True
    )
    scope: Mapped[str] = mapped_column(String(32), default="")
    question: Mapped[str] = mapped_column(String(2000))
    answer: Mapped[str] = mapped_column(Text, default="")
    grounding_status: Mapped[str] = mapped_column(String(32), default="")
    citation_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[str] = mapped_column(String(16), index=True)
    reason: Mapped[str] = mapped_column(String(512), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
