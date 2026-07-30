from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column, Enum as SAEnum, String
from sqlmodel import Field, Relationship, SQLModel


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

    id: int = Field(default=None, primary_key=True)
    email: str = Field(
        sa_column=Column(String(320), unique=True, index=True, nullable=False)
    )
    hashed_password: str = Field(sa_column=Column(String(1024), nullable=False))
    is_active: bool = Field(default=True, nullable=False)
    is_superuser: bool = Field(default=False, nullable=False)
    is_verified: bool = Field(default=False, nullable=False)

    collection: list["UserCard"] = Relationship(back_populates="user")


class Card(SQLModel, table=True):
    __tablename__ = "card"

    id: int = Field(default=None, primary_key=True)
    game: Game = Field(sa_column=Column(SAEnum(Game), nullable=False, index=True))
    name: str = Field(index=True)
    set_name: str
    set_code: str
    collector_number: str
    rarity: str = Field(default="Common")
    image_url: str = Field(default="")
    market_price: float = Field(default=0.0, ge=0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    game_metadata: dict = Field(default={}, sa_column=Column(JSON))

    user_cards: list["UserCard"] = Relationship(back_populates="card")


class UserCard(SQLModel, table=True):
    __tablename__ = "usercard"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False)
    card_id: int = Field(foreign_key="card.id", nullable=False)
    quantity: int = Field(default=1, ge=1)
    condition: Condition = Field(
        default=Condition.NEAR_MINT,
        sa_column=Column(SAEnum(Condition)),
    )
    is_foil: bool = Field(default=False)
    language: str = Field(default="EN", max_length=10)
    purchase_price: Optional[float] = Field(default=None)
    added_at: datetime = Field(default_factory=datetime.utcnow)

    user: User = Relationship(back_populates="collection")
    card: Card = Relationship(back_populates="user_cards")
