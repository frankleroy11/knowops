# 中文导读：
# 数据库迁移：用户、令牌与知识库成员
# upgrade 应用本次结构变更；downgrade 回退结构可能丢失对应字段或表中的数据，执行前需备份

"""Users, API tokens and per-knowledge-base membership."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "api_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("label", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_api_tokens_user_id", "api_tokens", ["user_id"])
    op.create_table(
        "kb_members",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kb_id", sa.Integer(), sa.ForeignKey("knowledge_bases.id"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kb_id", "user_id"),
    )
    op.create_index("ix_kb_members_kb_id", "kb_members", ["kb_id"])
    op.create_index("ix_kb_members_user_id", "kb_members", ["user_id"])
    op.add_column("knowledge_bases", sa.Column("owner_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_knowledge_bases_owner_id", "knowledge_bases", "users", ["owner_id"], ["id"]
    )
    op.add_column("documents", sa.Column("uploaded_by", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_documents_uploaded_by", "documents", "users", ["uploaded_by"], ["id"])


def downgrade():
    op.drop_constraint("fk_documents_uploaded_by", "documents", type_="foreignkey")
    op.drop_column("documents", "uploaded_by")
    op.drop_constraint("fk_knowledge_bases_owner_id", "knowledge_bases", type_="foreignkey")
    op.drop_column("knowledge_bases", "owner_id")
    op.drop_index("ix_kb_members_user_id", table_name="kb_members")
    op.drop_index("ix_kb_members_kb_id", table_name="kb_members")
    op.drop_table("kb_members")
    op.drop_index("ix_api_tokens_user_id", table_name="api_tokens")
    op.drop_table("api_tokens")
    op.drop_table("users")
