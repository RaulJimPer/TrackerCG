from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.models import Condition
from src.schemas.cards import CardResponse


class CollectionAddRequest(BaseModel):
    card_id: int
    quantity: int = Field(default=1, ge=1)
    condition: Condition = Condition.NEAR_MINT
    is_foil: bool = False
    language: str = Field(default="EN", max_length=10)
    purchase_price: Decimal | None = Field(default=None, ge=0)


class CollectionUpdateRequest(BaseModel):
    quantity: int | None = Field(default=None, ge=1)
    condition: Condition | None = None
    is_foil: bool | None = None
    language: str | None = Field(default=None, max_length=10)
    purchase_price: Decimal | None = Field(default=None, ge=0)


class CollectionSplitRequest(BaseModel):
    quantity: int = Field(default=1, ge=1)
    condition: Condition = Condition.NEAR_MINT
    is_foil: bool = False
    language: str = Field(default="EN", max_length=10)
    purchase_price: Decimal | None = Field(default=None, ge=0)


class CollectionItemResponse(BaseModel):
    id: int
    user_id: int
    card_id: int
    quantity: int
    condition: Condition
    is_foil: bool
    language: str
    purchase_price: Decimal | None
    added_at: datetime
    card: CardResponse
    total_value: Decimal

    model_config = {"from_attributes": True}


class CollectionListResult(BaseModel):
    items: list[CollectionItemResponse]
    total: int
    page: int
    page_size: int
    pages: int


class PortfolioValueResponse(BaseModel):
    total_value: Decimal
    cards_count: int
    unique_cards: int
