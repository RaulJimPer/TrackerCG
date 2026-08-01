"""Add unique index on usercard (user, card, condition, is_foil, language).

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-01
"""
from __future__ import annotations

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_usercard_user_card_variant"
VARIANT_COLUMNS = ("user_id", "card_id", "condition", "is_foil", "language")


def _dedupe_variants(connection) -> None:
    """Merge duplicate (user, card, variant) rows before creating the unique index.

    For each duplicate group the earliest row keeps the summed quantity and the
    remaining rows are deleted. Safe to run when no duplicates exist.
    """
    cols = ", ".join(VARIANT_COLUMNS)
    where = " AND ".join(f"{c} = ?" for c in VARIANT_COLUMNS)
    groups = connection.exec_driver_sql(
        f"SELECT {cols}, COUNT(*) FROM usercard "
        f"GROUP BY {cols} HAVING COUNT(*) > 1"
    ).fetchall()
    for group in groups:
        *keys, _count = group
        dupes = connection.exec_driver_sql(
            f"SELECT id, quantity FROM usercard WHERE {where} "
            "ORDER BY id",
            tuple(keys),
        ).fetchall()
        keep_id, _ = dupes[0]
        total = sum(qty for _, qty in dupes)
        connection.exec_driver_sql(
            "UPDATE usercard SET quantity = ? WHERE id = ?", (total, keep_id)
        )
        for dup_id, _ in dupes[1:]:
            connection.exec_driver_sql("DELETE FROM usercard WHERE id = ?", (dup_id,))


def upgrade() -> None:
    bind = op.get_bind()
    _dedupe_variants(bind)
    op.create_index(INDEX_NAME, "usercard", list(VARIANT_COLUMNS), unique=True)


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="usercard")
