"""add transaction splits

Revision ID: 20260212_0007
Revises: 20260212_0006
Create Date: 2026-02-12 00:07:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260212_0007"
down_revision = "20260212_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transaction_splits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.CheckConstraint("amount > 0", name="ck_transaction_splits_amount_positive"),
    )
    op.create_index(
        "ix_transaction_splits_transaction_id",
        "transaction_splits",
        ["transaction_id"],
    )
    op.create_index(
        "ix_transaction_splits_category_id",
        "transaction_splits",
        ["category_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transaction_splits_category_id", table_name="transaction_splits")
    op.drop_index("ix_transaction_splits_transaction_id", table_name="transaction_splits")
    op.drop_table("transaction_splits")
