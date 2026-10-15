# 中文导读：
# 数据库迁移：审核状态与审计记录
# upgrade 应用本次结构变更；downgrade 回退结构可能丢失对应字段或表中的数据，执行前需备份

"""Per-KB review workflow, version publish state and audit trail."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "knowledge_bases",
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column("documents", sa.Column("retired_at", sa.DateTime(), nullable=True))
    op.add_column(
        "document_versions",
        sa.Column(
            "review_status", sa.String(32), nullable=False, server_default="approved"
        ),
    )
    op.add_column(
        "document_versions",
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    )
    op.add_column("document_versions", sa.Column("uploaded_by", sa.Integer(), nullable=True))
    op.add_column("document_versions", sa.Column("reviewed_by", sa.Integer(), nullable=True))
    op.add_column("document_versions", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.add_column("document_versions", sa.Column("review_note", sa.String(512), nullable=True))
    op.create_foreign_key(
        "fk_document_versions_uploaded_by", "document_versions", "users", ["uploaded_by"], ["id"]
    )
    op.create_foreign_key(
        "fk_document_versions_reviewed_by", "document_versions", "users", ["reviewed_by"], ["id"]
    )
    op.create_index("ix_document_versions_is_current", "document_versions", ["is_current"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_email", sa.String(255), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("object_type", sa.String(32), nullable=False),
        sa.Column("object_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])

    # Existing content was already live under the pre-P2 rules.
    op.execute("update document_versions set review_status='approved', is_current=1")
    op.execute("update knowledge_bases set review_required=0")


def downgrade():
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index("ix_document_versions_is_current", table_name="document_versions")
    op.drop_constraint(
        "fk_document_versions_reviewed_by", "document_versions", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_document_versions_uploaded_by", "document_versions", type_="foreignkey"
    )
    for column in (
        "review_note",
        "reviewed_at",
        "reviewed_by",
        "uploaded_by",
        "is_current",
        "review_status",
    ):
        op.drop_column("document_versions", column)
    op.drop_column("documents", "retired_at")
    op.drop_column("knowledge_bases", "review_required")
