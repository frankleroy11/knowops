# 中文导读：
# 数据库迁移：问答反馈快照
# upgrade 应用本次结构变更；downgrade 回退结构可能丢失对应字段或表中的数据，执行前需备份

"""Answer feedback table backing the online evaluation loop."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "answer_feedback",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column(
            "knowledge_base_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_bases.id"),
            nullable=True,
        ),
        sa.Column("scope", sa.String(32), nullable=False),
        sa.Column("question", sa.String(2000), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("grounding_status", sa.String(32), nullable=False),
        sa.Column("citation_count", sa.Integer(), nullable=False),
        sa.Column("rating", sa.String(16), nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    for column in ("user_id", "tenant_id", "knowledge_base_id", "rating"):
        op.create_index(f"ix_answer_feedback_{column}", "answer_feedback", [column])


def downgrade():
    op.drop_table("answer_feedback")
