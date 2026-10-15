"""Tenant partition for the audit trail."""

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("audit_logs", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_audit_logs_tenant_id", "audit_logs", "tenants", ["tenant_id"], ["id"])
    op.create_index("ix_audit_logs_tenant_id", "audit_logs", ["tenant_id"])
    # Historic rows inherit the actor's tenant; platform-level actors stay NULL.
    op.execute(
        "update audit_logs set tenant_id = "
        "(select tenant_id from users where users.id = audit_logs.actor_id) "
        "where tenant_id is null and actor_id is not null"
    )


def downgrade():
    op.drop_index("ix_audit_logs_tenant_id", table_name="audit_logs")
    op.drop_constraint("fk_audit_logs_tenant_id", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "tenant_id")
