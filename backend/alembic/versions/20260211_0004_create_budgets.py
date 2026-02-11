"""create budgets table

Revision ID: 20260211_0004
Revises: 20260210_0003
Create Date: 2026-02-11 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260211_0004"
down_revision = "20260210_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("month_start", sa.Date(), nullable=False),
        sa.Column("limit_amount", sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("limit_amount > 0", name="ck_budgets_limit_amount_positive"),
        sa.CheckConstraint(
            "month_start = date_trunc('month', month_start::timestamp)::date",
            name="ck_budgets_month_start_first_day",
        ),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "category_id",
            "month_start",
            name="uq_budgets_user_id_category_id_month_start",
        ),
    )
    op.create_index(
        "ix_budgets_user_id_month_start",
        "budgets",
        ["user_id", "month_start"],
        unique=False,
    )
    op.create_index("ix_budgets_category_id", "budgets", ["category_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_budgets_category_id", table_name="budgets")
    op.drop_index("ix_budgets_user_id_month_start", table_name="budgets")
    op.drop_table("budgets")
