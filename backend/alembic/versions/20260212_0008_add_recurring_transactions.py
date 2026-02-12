"""add recurring transactions

Revision ID: 20260212_0008
Revises: 20260212_0007
Create Date: 2026-02-12 00:08:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260212_0008"
down_revision = "20260212_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recurring_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("direction", sa.String(length=3), nullable=False),
        sa.Column("cadence", sa.String(length=10), nullable=False),
        sa.Column("interval", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("merchant", sa.String(length=200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("tags", postgresql.ARRAY(sa.String(length=32)), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.CheckConstraint("amount > 0", name="ck_recurring_transactions_amount_positive"),
        sa.CheckConstraint(
            "direction IN ('IN', 'OUT')",
            name="ck_recurring_transactions_direction_valid",
        ),
        sa.CheckConstraint(
            "cadence IN ('DAILY', 'WEEKLY', 'MONTHLY')",
            name="ck_recurring_transactions_cadence_valid",
        ),
        sa.CheckConstraint(
            "interval > 0",
            name="ck_recurring_transactions_interval_positive",
        ),
    )
    op.create_index(
        "ix_recurring_transactions_user_id_next_run_at",
        "recurring_transactions",
        ["user_id", "next_run_at"],
    )
    op.create_index(
        "ix_recurring_transactions_account_id",
        "recurring_transactions",
        ["account_id"],
    )
    op.create_index(
        "ix_recurring_transactions_active",
        "recurring_transactions",
        ["user_id", "is_active"],
    )


def downgrade() -> None:
    op.drop_index("ix_recurring_transactions_active", table_name="recurring_transactions")
    op.drop_index(
        "ix_recurring_transactions_account_id",
        table_name="recurring_transactions",
    )
    op.drop_index(
        "ix_recurring_transactions_user_id_next_run_at",
        table_name="recurring_transactions",
    )
    op.drop_table("recurring_transactions")
