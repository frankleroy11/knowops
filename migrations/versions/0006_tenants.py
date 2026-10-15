"""Tenants: every knowledge base and user belongs to one organization.

NULL `users.tenant_id` marks a platform-level account that may administer all
tenants; `knowledge_bases.tenant_id` is always set.
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("name"),
        sa.UniqueConstraint("slug"),
    )
    op.add_column("users", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_users_tenant_id", "users", "tenants", ["tenant_id"], ["id"])
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.add_column("knowledge_bases", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_knowledge_bases_tenant_id", "knowledge_bases", "tenants", ["tenant_id"], ["id"]
    )
    op.create_index("ix_knowledge_bases_tenant_id", "knowledge_bases", ["tenant_id"])

    # Existing rows belong to a single default tenant, so nothing changes for them.
    op.execute(
        "insert into tenants (name, slug, is_active) values ('默认租户', 'default', 1)"
    )
    op.execute(
        "update users set tenant_id = (select id from tenants where slug = 'default') "
        "where tenant_id is null"
    )
    op.execute(
        "update knowledge_bases set tenant_id = (select id from tenants where slug = 'default') "
        "where tenant_id is null"
    )
    op.alter_column(
        "knowledge_bases", "tenant_id", existing_type=sa.Integer(), nullable=False
    )


def downgrade():
    op.alter_column(
        "knowledge_bases", "tenant_id", existing_type=sa.Integer(), nullable=True
    )
    op.drop_index("ix_knowledge_bases_tenant_id", table_name="knowledge_bases")
    op.drop_constraint("fk_knowledge_bases_tenant_id", "knowledge_bases", type_="foreignkey")
    op.drop_column("knowledge_bases", "tenant_id")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_constraint("fk_users_tenant_id", "users", type_="foreignkey")
    op.drop_column("users", "tenant_id")
    op.drop_table("tenants")
