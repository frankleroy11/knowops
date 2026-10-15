# 中文导读：
# 数据库迁移：向量索引状态
# upgrade 应用本次结构变更；downgrade 回退结构可能丢失对应字段或表中的数据，执行前需备份

"""Independent per-model indexing state."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "vector_indexes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "version_id", sa.Integer(), sa.ForeignKey("document_versions.id"), nullable=False
        ),
        sa.Column("collection", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("chunks_indexed", sa.Integer(), nullable=False),
        sa.Column("error", sa.String(512), nullable=True),
        sa.UniqueConstraint("version_id", "collection"),
    )
    op.create_index("ix_vector_indexes_version_id", "vector_indexes", ["version_id"])


def downgrade():
    op.drop_table("vector_indexes")
