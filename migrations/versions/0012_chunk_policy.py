"""Persist the chunk policy for reproducible version ingestion."""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "document_versions",
        sa.Column("chunk_strategy", sa.String(32), nullable=False, server_default="fixed"),
    )
    op.add_column(
        "document_versions",
        sa.Column("chunk_size", sa.Integer(), nullable=False, server_default="800"),
    )
    op.add_column(
        "document_versions",
        sa.Column("chunk_overlap", sa.Integer(), nullable=False, server_default="100"),
    )


def downgrade():
    for name in ("chunk_overlap", "chunk_size", "chunk_strategy"):
        op.drop_column("document_versions", name)
