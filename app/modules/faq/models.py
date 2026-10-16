"""FAQ 保存在 MySQL，绑定当前有效的证据块；向量只是问题的派生索引。"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Faq(Base):
    __tablename__ = "faqs"
    id: Mapped[int] = mapped_column(primary_key=True)
    knowledge_base_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_bases.id", ondelete="CASCADE"), index=True
    )
    chunk_id: Mapped[int] = mapped_column(ForeignKey("chunks.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(String(2000))
    answer: Mapped[str] = mapped_column(Text)
    quote: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    question_vector: Mapped[list] = mapped_column(JSON)
    embedding_identity: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
