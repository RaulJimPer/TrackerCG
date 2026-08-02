"""initial schema: user, card, usercard

Revision ID: 0001
Revises:
Create Date: 2026-07-31

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401
from sqlalchemy.dialects import sqlite

from src.models import Condition, Game

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_user() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("hashed_password", sa.String(length=1024), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("is_superuser", sa.Boolean(), nullable=False),
        sa.Column("is_verified", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)


def _create_card() -> None:
    op.create_table(
        "card",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game", sa.Enum(Game), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("set_name", sa.String(), nullable=False),
        sa.Column("set_code", sa.String(), nullable=False),
        sa.Column("collector_number", sa.String(), nullable=False),
        sa.Column("rarity", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=False),
        sa.Column("market_price", sa.Float(), nullable=False),
        sa.Column("last_updated", sa.DateTime(), nullable=False),
        sa.Column("game_metadata", sqlite.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_card_game"), "card", ["game"], unique=False)
    op.create_index(op.f("ix_card_name"), "card", ["name"], unique=False)
    op.create_index(
        "uq_card_game_external_id",
        "card",
        ["game", "external_id"],
        unique=True,
        sqlite_where=sa.text("external_id <> ''"),
    )


def _create_usercard() -> None:
    op.create_table(
        "usercard",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("card_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("condition", sa.Enum(Condition), nullable=False),
        sa.Column("is_foil", sa.Boolean(), nullable=False),
        sa.Column("language", sa.String(length=10), nullable=False),
        sa.Column("purchase_price", sa.Float(), nullable=True),
        sa.Column("added_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["card.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usercard_user_id"), "usercard", ["user_id"], unique=False)
    op.create_index(op.f("ix_usercard_card_id"), "usercard", ["card_id"], unique=False)


def _backfill_external_id() -> None:
    op.execute(
        """
        UPDATE card
        SET external_id = CASE
            WHEN game = 'POKEMON' THEN COALESCE(json_extract(game_metadata, '$.id'), '')
            WHEN game = 'YUGIOH' THEN COALESCE(json_extract(game_metadata, '$.tcgplayer_id'), '')
            WHEN game = 'MTG' THEN COALESCE(set_code, '') || '/' || COALESCE(collector_number, '')
            ELSE external_id
        END
        WHERE external_id = ''
        """
    )


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("user"):
        _create_user()
    else:
        columns = {c["name"] for c in inspector.get_columns("user")}
        if "is_verified" not in columns:
            op.add_column("user", sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()))
        indexes = {ix["name"] for ix in inspector.get_indexes("user")}
        if "ix_user_email" not in indexes:
            op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    if not inspector.has_table("card"):
        _create_card()
    else:
        columns = {c["name"] for c in inspector.get_columns("card")}
        if "external_id" not in columns:
            op.add_column(
                "card",
                sa.Column("external_id", sa.String(length=255), nullable=False, server_default=""),
            )
        indexes = {ix["name"] for ix in inspector.get_indexes("card")}
        if "ix_card_game" not in indexes:
            op.create_index(op.f("ix_card_game"), "card", ["game"], unique=False)
        if "ix_card_name" not in indexes:
            op.create_index(op.f("ix_card_name"), "card", ["name"], unique=False)
        if "uq_card_game_external_id" not in indexes:
            op.create_index(
                "uq_card_game_external_id",
                "card",
                ["game", "external_id"],
                unique=True,
                sqlite_where=sa.text("external_id <> ''"),
            )
        _backfill_external_id()

    if not inspector.has_table("usercard"):
        _create_usercard()
    else:
        indexes = {ix["name"] for ix in inspector.get_indexes("usercard")}
        if "ix_usercard_user_id" not in indexes:
            op.create_index(op.f("ix_usercard_user_id"), "usercard", ["user_id"], unique=False)
        if "ix_usercard_card_id" not in indexes:
            op.create_index(op.f("ix_usercard_card_id"), "usercard", ["card_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("usercard"):
        op.drop_index(op.f("ix_usercard_card_id"), table_name="usercard")
        op.drop_index(op.f("ix_usercard_user_id"), table_name="usercard")
        op.drop_table("usercard")
    if inspector.has_table("card"):
        op.drop_index("uq_card_game_external_id", table_name="card")
        op.drop_index(op.f("ix_card_name"), table_name="card")
        op.drop_index(op.f("ix_card_game"), table_name="card")
        op.drop_table("card")
    if inspector.has_table("user"):
        op.drop_index(op.f("ix_user_email"), table_name="user")
        op.drop_table("user")
