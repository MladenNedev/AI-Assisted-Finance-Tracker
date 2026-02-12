"""add transaction tags

Revision ID: 20260212_0006
Revises: 20260212_0005
Create Date: 2026-02-12 00:06:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260212_0006"
down_revision = "20260212_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String(length=32)),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_transactions_tags",
        "transactions",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_tags", table_name="transactions")
    op.drop_column("transactions", "tags")
