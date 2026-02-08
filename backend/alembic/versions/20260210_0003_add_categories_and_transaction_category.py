"""add categories and transaction category reference

Revision ID: 20260210_0003
Revises: 20260209_0002
Create Date: 2026-02-10 00:00:00.000000

"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260210_0003"
down_revision = "20260209_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("is_income", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("color", sa.String(length=7), nullable=True),
        sa.Column("icon", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_categories_user_id_name"),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"], unique=False)
    op.create_index(
        "ix_categories_user_id_is_income",
        "categories",
        ["user_id", "is_income"],
        unique=False,
    )

    op.add_column(
        "transactions",
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_category_id_categories",
        "transactions",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_transactions_category_id", "transactions", ["category_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transactions_category_id", table_name="transactions")
    op.drop_constraint(
        "fk_transactions_category_id_categories",
        "transactions",
        type_="foreignkey",
    )
    op.drop_column("transactions", "category_id")

    op.drop_index("ix_categories_user_id_is_income", table_name="categories")
    op.drop_index("ix_categories_user_id", table_name="categories")
    op.drop_table("categories")
