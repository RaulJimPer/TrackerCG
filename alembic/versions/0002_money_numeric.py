"""money columns as Numeric(10,2) for SQLite schema consistency

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-31

Note: SQLite does not enforce column types, so this migration is
schema-consistency only (matches the SQLModel Numeric(10,2) columns).
The partial unique index is explicitly recreated to preserve its
predicate (external_id <> ''), which SQLAlchemy reflection cannot read.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_float_column(inspector: sa.Inspector, table: str, column: str) -> bool:
    columns = {c["name"]: c["type"] for c in inspector.get_columns(table)}
    col_type = columns.get(column)
    return isinstance(col_type, sa.types.Float)


def _has_partial_index(bind) -> bool:
    rows = bind.exec_driver_sql(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_card_game_external_id'"
    ).fetchall()
    return bool(rows) and "external_id <> ''" in (rows[0][0] or "")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("card") and _has_float_column(inspector, "card", "market_price"):
        with op.batch_alter_table("card") as batch:
            batch.drop_index("uq_card_game_external_id")
            batch.alter_column(
                "market_price",
                existing_type=sa.Float(),
                type_=sa.Numeric(10, 2),
                existing_nullable=False,
            )
            batch.create_index(
                "uq_card_game_external_id",
                ["game", "external_id"],
                unique=True,
                sqlite_where=sa.text("external_id <> ''"),
            )

    if inspector.has_table("usercard") and _has_float_column(inspector, "usercard", "purchase_price"):
        with op.batch_alter_table("usercard") as batch:
            batch.alter_column(
                "purchase_price",
                existing_type=sa.Float(),
                type_=sa.Numeric(10, 2),
                existing_nullable=True,
            )

    # Self-heal: recreate the partial unique index if a previous batch run
    # dropped its predicate.
    if inspector.has_table("card") and not _has_partial_index(bind):
        op.create_index(
            "uq_card_game_external_id",
            "card",
            ["game", "external_id"],
            unique=True,
            sqlite_where=sa.text("external_id <> ''"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("card") and not _has_float_column(inspector, "card", "market_price"):
        with op.batch_alter_table("card") as batch:
            batch.drop_index("uq_card_game_external_id")
            batch.alter_column(
                "market_price",
                existing_type=sa.Numeric(10, 2),
                type_=sa.Float(),
                existing_nullable=False,
            )
            batch.create_index(
                "uq_card_game_external_id",
                ["game", "external_id"],
                unique=True,
                sqlite_where=sa.text("external_id <> ''"),
            )

    if inspector.has_table("usercard") and not _has_float_column(inspector, "usercard", "purchase_price"):
        with op.batch_alter_table("usercard") as batch:
            batch.alter_column(
                "purchase_price",
                existing_type=sa.Numeric(10, 2),
                type_=sa.Float(),
                existing_nullable=True,
            )
