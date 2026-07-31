from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_async_session
from src.models import Card, Game
from src.schemas.cards import CardResponse, CardSearchResult
from src.scraper import refresh_card_price, search_cards

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.get("/search", response_model=CardSearchResult)
async def api_search_cards(
    q: str = Query("", description="Generic search query"),
    game: Game | None = Query(None, description="Filter by game"),
    name: str = Query("", description="Search by card name"),
    set_name: str = Query("", description="Search by set name"),
    collector_number: str = Query("", description="Search by collector number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_session),
):
    query = q or name or set_name or collector_number
    game_enum: Game | None = game

    if query:
        return await _search_external(db, game_enum, query, page, page_size)

    return await _search_local(db, game_enum, name, set_name, collector_number, page, page_size)


async def _search_external(
    db: AsyncSession,
    game: Game | None,
    query: str,
    page: int,
    page_size: int,
) -> CardSearchResult:
    if game is None:
        return CardSearchResult(items=[], total=0, page=page, page_size=page_size, pages=0)

    cards = await search_cards(db, game, query)

    total = len(cards)
    pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    end = start + page_size
    page_items = [CardResponse.model_validate(c) for c in cards[start:end]]

    return CardSearchResult(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


async def _search_local(
    db: AsyncSession,
    game: Game | None,
    name: str,
    set_name: str,
    collector_number: str,
    page: int,
    page_size: int,
) -> CardSearchResult:
    stmt = select(Card)

    conditions = []
    if game is not None:
        conditions.append(Card.game == game)
    if name:
        conditions.append(Card.name.ilike(f"%{name}%"))
    if set_name:
        conditions.append(Card.set_name.ilike(f"%{set_name}%"))
    if collector_number:
        conditions.append(Card.collector_number.ilike(f"%{collector_number}%"))

    if conditions:
        stmt = stmt.where(*conditions)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    pages = max(1, math.ceil(total / page_size))

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    cards = list(result.scalars().all())

    return CardSearchResult(
        items=[CardResponse.model_validate(c) for c in cards],
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/{card_id}", response_model=CardResponse)
async def api_get_card(
    card_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    stmt = select(Card).where(Card.id == card_id)
    result = await db.execute(stmt)
    card = result.scalar_one_or_none()
    return CardResponse.model_validate(card)


@router.post("/{card_id}/refresh-price")
async def api_refresh_price(
    card_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    stmt = select(Card).where(Card.id == card_id)
    result = await db.execute(stmt)
    card = result.scalar_one_or_none()
    if card is None:
        return {"error": "Card not found"}
    price = await refresh_card_price(db, card)
    return {"card_id": card_id, "market_price": price}
