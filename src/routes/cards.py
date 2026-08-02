import math

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_user
from src.database import get_async_session
from src.models import Card, Game, User
from src.rate_limit import limiter
from src.schemas.cards import CardResponse, CardSearchResult, PriceRefreshResponse
from src.scraper import SCRAPERS, refresh_card_price, search_cards

router = APIRouter(prefix="/api/cards", tags=["cards"])


def _pages(total: int, page_size: int) -> int:
    if total == 0:
        return 0
    return math.ceil(total / page_size)


@router.get("/search", response_model=CardSearchResult)
@limiter.limit("30/minute")
async def api_search_cards(
    request: Request,
    response: Response,
    q: str = Query("", max_length=200, description="Generic search query"),
    game: Game | None = Query(None, description="Filter by game"),
    name: str = Query("", max_length=200, description="Search by card name"),
    set_name: str = Query("", max_length=200, description="Search by set name"),
    collector_number: str = Query("", max_length=100, description="Search by collector number"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
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
    cards = await search_cards(db, game, query)

    total = len(cards)
    start = (page - 1) * page_size
    end = start + page_size
    page_items = [CardResponse.model_validate(c) for c in cards[start:end]]

    return CardSearchResult(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        pages=_pages(total, page_size),
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

    stmt = (
        stmt.order_by(Card.game, Card.name, Card.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    cards = list(result.scalars().all())

    return CardSearchResult(
        items=[CardResponse.model_validate(c) for c in cards],
        total=total,
        page=page,
        page_size=page_size,
        pages=_pages(total, page_size),
    )


@router.get("/{card_id}", response_model=CardResponse)
@limiter.limit("60/minute")
async def api_get_card(
    request: Request,
    response: Response,
    card_id: int,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    card = await db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return CardResponse.model_validate(card)


@router.post("/{card_id}/refresh-price", response_model=PriceRefreshResponse)
@limiter.limit("20/minute")
async def api_refresh_price(
    request: Request,
    response: Response,
    card_id: int,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    card = await db.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    if card.game not in SCRAPERS:
        raise HTTPException(
            status_code=400,
            detail=f"No price source available for game {card.game.value}",
        )
    price = await refresh_card_price(db, card)
    return PriceRefreshResponse(card_id=card_id, market_price=price)
