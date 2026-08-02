from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    TypeDecorator,
    UniqueConstraint,
    text,
)
from sqlmodel import Field, SQLModel


class UTCDateTime(TypeDecorator):
    """Stores naive UTC datetimes in SQLite, returns timezone-aware UTC."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None:
            if value.tzinfo is None:
                value = value.replace(tzinfo=timezone.utc)
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Game(str, Enum):
    MTG = "MTG"
    POKEMON = "POKEMON"
    YUGIOH = "YUGIOH"
    LORCANA = "LORCANA"
    ONEPIECE = "ONEPIECE"
    DIGIMON = "DIGIMON"
    FLESH_AND_BLOOD = "FLESH_AND_BLOOD"
    VANGUARD = "VANGUARD"
    WEISS_SCHWARZ = "WEISS_SCHWARZ"
    DBS = "DBS"
    FF_TCG = "FF_TCG"
    FORCE_OF_WILL = "FORCE_OF_WILL"
    L5R = "L5R"
    BATTLE_SPIRITS = "BATTLE_SPIRITS"
    GUNDAM = "GUNDAM"
    STAR_WARS = "STAR_WARS"
    KEYFORGE = "KEYFORGE"
    SORCERY = "SORCERY"
    OTHER = "OTHER"


class Condition(str, Enum):
    MINT = "Mint"
    NEAR_MINT = "Near Mint"
    LIGHTLY_PLAYED = "Lightly Played"
    PLAYED = "Played"
    DAMAGED = "Damaged"


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(
        sa_column=Column(String(320), unique=True, index=True, nullable=False)
    )
    hashed_password: str = Field(sa_column=Column(String(1024), nullable=False))
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    is_verified: bool = Field(default=False, nullable=False)


class Card(SQLModel, table=True):
    __tablename__ = "card"
    __table_args__ = (
        Index(
            "uq_card_game_external_id",
            "game",
            "external_id",
            unique=True,
            sqlite_where=text("external_id <> ''"),
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    game: Game = Field(sa_column=Column(SAEnum(Game), nullable=False, index=True))
    external_id: str = Field(default="", max_length=255)
    name: str = Field(index=True)
    set_name: str
    set_code: str
    collector_number: str
    rarity: str = Field(default="Common")
    image_url: str = Field(default="")
    market_price: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        sa_column=Column(Numeric(10, 2), nullable=False),
    )
    last_updated: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(UTCDateTime(), nullable=False),
    )
    game_metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))


class UserCard(SQLModel, table=True):
    __tablename__ = "usercard"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "card_id",
            "condition",
            "is_foil",
            "language",
            name="uq_usercard_user_card_variant",
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    card_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("card.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    quantity: int = Field(default=1, ge=1)
    condition: Condition = Field(
        default=Condition.NEAR_MINT,
        sa_column=Column(SAEnum(Condition)),
    )
    is_foil: bool = Field(default=False)
    language: str = Field(default="EN", max_length=10)
    purchase_price: Decimal | None = Field(
        default=None,
        sa_column=Column(Numeric(10, 2), nullable=True),
    )
    added_at: datetime = Field(
        default_factory=utcnow,
        sa_column=Column(UTCDateTime(), nullable=False),
    )
