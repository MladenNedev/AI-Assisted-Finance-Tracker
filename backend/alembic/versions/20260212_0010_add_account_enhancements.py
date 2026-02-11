"""add account enhancements

Revision ID: 20260212_0010
Revises: 20260212_0009
Create Date: 2026-02-12 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260212_0010"
down_revision = "20260212_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("accounts", sa.Column("color", sa.String(length=7)))
    op.add_column("accounts", sa.Column("icon", sa.String(length=50)))
    op.add_column("accounts", sa.Column("goal_name", sa.String(length=100)))
    op.add_column("accounts", sa.Column("goal_target_amount", sa.Numeric(18, 2)))
    op.add_column("accounts", sa.Column("goal_target_date", sa.Date()))


def downgrade() -> None:
    op.drop_column("accounts", "goal_target_date")
    op.drop_column("accounts", "goal_target_amount")
    op.drop_column("accounts", "goal_name")
    op.drop_column("accounts", "icon")
    op.drop_column("accounts", "color")
