"""Trim Game enum to the four supported TCGs and drop out-of-scope rows.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-05

The app now only supports MTG, POKEMON, YUGIOH and RIFTBOUND. SQLite stores
the game column as a plain VARCHAR without a CHECK constraint, so no schema
change is required; the Python enum is the source of truth. Rows for games
outside the new scope are removed (usercard first — foreign keys are OFF
during the migration window, so CASCADE would not fire).

"""
from __future__ import annotations

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SUPPORTED_GAMES = ("MTG", "POKEMON", "YUGIOH", "RIFTBOUND")


def upgrade() -> None:
    bind = op.get_bind()
    placeholders = ",".join("?" for _ in SUPPORTED_GAMES)
    bind.exec_driver_sql(
        f"DELETE FROM usercard WHERE card_id IN "
        f"(SELECT id FROM card WHERE game NOT IN ({placeholders}))",
        SUPPORTED_GAMES,
    )
    bind.exec_driver_sql(
        f"DELETE FROM card WHERE game NOT IN ({placeholders})",
        SUPPORTED_GAMES,
    )


def downgrade() -> None:
    # Deleted rows cannot be restored; the enum values they used were removed.
    pass
