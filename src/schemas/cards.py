from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.models import Game


class CardSearchParams(BaseModel):
    q: str = ""
    name: str = ""
    set_name: str = ""
    collector_number: str = ""
    game: Game | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class CardResponse(BaseModel):
    id: int
    game: Game
    name: str
    set_name: str
    set_code: str
    collector_number: str
    rarity: str
    image_url: str
    market_price: float
    last_updated: datetime
    game_metadata: dict[str, Any]

    model_config = {"from_attributes": True}


class CardSearchResult(BaseModel):
    items: list[CardResponse]
    total: int
    page: int
    page_size: int
    pages: int
