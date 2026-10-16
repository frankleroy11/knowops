"""增加带来源证据的标准 FAQ；回退会删除 FAQ 数据。"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "faqs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "knowledge_base_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id", sa.Integer(), sa.ForeignKey("chunks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("question", sa.String(2000), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("question_vector", sa.JSON(), nullable=False),
        sa.Column("embedding_identity", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_faqs_knowledge_base_id", "faqs", ["knowledge_base_id"])
    op.create_index("ix_faqs_chunk_id", "faqs", ["chunk_id"])


def downgrade():
    op.drop_table("faqs")
