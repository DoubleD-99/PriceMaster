"""add analytics indexes (B-12)

Revision ID: a7b8c9d0e1f2
Revises: 1e73494c7c9c
Create Date: 2026-11-18 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: str | Sequence[str] | None = "1e73494c7c9c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_price_history_store_id", "price_history", ["store_id"], unique=False
    )
    op.create_index(
        "ix_price_history_product_id", "price_history", ["product_id"], unique=False
    )
    op.create_index(
        "ix_price_history_changed_at", "price_history", ["changed_at"], unique=False
    )
    op.create_index(
        "ix_external_factors_store_id", "external_factors", ["store_id"], unique=False
    )
    op.create_index(
        "ix_external_factors_date", "external_factors", ["date"], unique=False
    )
    op.create_index(
        "ix_external_factors_store_date",
        "external_factors",
        ["store_id", "date"],
        unique=False,
    )
    op.create_index(
        "ix_price_recommendations_store_id",
        "price_recommendations",
        ["store_id"],
        unique=False,
    )
    op.create_index(
        "ix_price_recommendations_store_status",
        "price_recommendations",
        ["store_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_price_recommendations_created_at",
        "price_recommendations",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_price_recommendations_created_at", table_name="price_recommendations"
    )
    op.drop_index(
        "ix_price_recommendations_store_status", table_name="price_recommendations"
    )
    op.drop_index(
        "ix_price_recommendations_store_id", table_name="price_recommendations"
    )
    op.drop_index("ix_external_factors_store_date", table_name="external_factors")
    op.drop_index("ix_external_factors_date", table_name="external_factors")
    op.drop_index("ix_external_factors_store_id", table_name="external_factors")
    op.drop_index("ix_price_history_changed_at", table_name="price_history")
    op.drop_index("ix_price_history_product_id", table_name="price_history")
    op.drop_index("ix_price_history_store_id", table_name="price_history")
