"""add transaction attachments

Revision ID: 20260212_0009
Revises: 20260212_0008
Create Date: 2026-02-12 00:09:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260212_0009"
down_revision = "20260212_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transaction_attachments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=100), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("storage_key", name="uq_transaction_attachments_storage_key"),
    )
    op.create_index(
        "ix_transaction_attachments_transaction_id",
        "transaction_attachments",
        ["transaction_id"],
    )
    op.create_index(
        "ix_transaction_attachments_user_id",
        "transaction_attachments",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_attachments_user_id", table_name="transaction_attachments")
    op.drop_index(
        "ix_transaction_attachments_transaction_id",
        table_name="transaction_attachments",
    )
    op.drop_table("transaction_attachments")
