"""add budget rollover flag and transfer id

Revision ID: 20260212_0005
Revises: 20260211_0004
Create Date: 2026-02-12 00:00:00.000000

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260212_0005"
down_revision = "20260211_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "budgets",
        sa.Column(
            "rollover_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "transactions",
        sa.Column("transfer_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_transactions_transfer_id",
        "transactions",
        ["transfer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_transfer_id", table_name="transactions")
    op.drop_column("transactions", "transfer_id")
    op.drop_column("budgets", "rollover_enabled")
