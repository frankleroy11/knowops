# 中文导读：
# 数据库迁移：OIDC 身份与登录状态
# upgrade 应用本次结构变更；downgrade 回退结构可能丢失对应字段或表中的数据，执行前需备份

"""OIDC single sign-on: login state, ID-token verification and account mapping."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "oidc_login_states",
        sa.Column("state", sa.String(64), primary_key=True),
        sa.Column("nonce", sa.String(64), nullable=False),
        sa.Column("web", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
    )
    op.add_column("users", sa.Column("oidc_issuer", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("oidc_subject", sa.String(255), nullable=True))
    op.create_unique_constraint(
        "uq_users_oidc_identity", "users", ["oidc_issuer", "oidc_subject"]
    )


def downgrade():
    op.drop_constraint("uq_users_oidc_identity", "users", type_="unique")
    op.drop_column("users", "oidc_subject")
    op.drop_column("users", "oidc_issuer")
    op.drop_table("oidc_login_states")
