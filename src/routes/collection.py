from __future__ import annotations

import asyncio
import math
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_user
from src.database import get_async_session
from src.models import Card, Game, User, UserCard
from src.schemas.collection import (
    CollectionAddRequest,
    CollectionItemResponse,
    CollectionListResult,
    CollectionSplitRequest,
    CollectionUpdateRequest,
    PortfolioValueResponse,
)
from src.schemas.cards import CardResponse
from src.scraper import SCRAPERS, refresh_stale_prices

router = APIRouter(prefix="/api/collection", tags=["collection"])


def _pages(total: int, page_size: int) -> int:
    if total == 0:
        return 0
    return math.ceil(total / page_size)


def _item_response(uc: UserCard, card: Card) -> CollectionItemResponse:
    return CollectionItemResponse(
        id=uc.id,
        user_id=uc.user_id,
        card_id=uc.card_id,
        quantity=uc.quantity,
        condition=uc.condition,
        is_foil=uc.is_foil,
        language=uc.language,
        purchase_price=uc.purchase_price,
        added_at=uc.added_at,
        card=CardResponse.model_validate(card),
        total_value=(uc.quantity * card.market_price).quantize(Decimal("0.01")),
    )


@router.get("", response_model=CollectionListResult)
async def list_collection(
    game: Game | None = Query(None, description="Filter by game"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    joined = (
        select(UserCard, Card)
        .join(Card, UserCard.card_id == Card.id)
        .where(UserCard.user_id == user.id)
    )

    if game is not None:
        joined = joined.where(Card.game == game)

    count_stmt = select(func.count()).select_from(joined.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    query = (
        joined.order_by(UserCard.added_at.desc(), UserCard.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()

    enriched = []
    for uc, card in rows:
        if card is None:
            continue
        enriched.append(_item_response(uc, card))

    return CollectionListResult(
        items=enriched,
        total=total,
        page=page,
        page_size=page_size,
        pages=_pages(total, page_size),
    )


@router.get("/games", response_model=list[str])
async def collection_games(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    """Distinct games present in the current user's collection."""
    stmt = (
        select(func.distinct(Card.game))
        .select_from(UserCard)
        .join(Card, UserCard.card_id == Card.id)
        .where(UserCard.user_id == user.id)
        .order_by(Card.game)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/value", response_model=PortfolioValueResponse)
async def portfolio_value(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    stmt = select(
        func.coalesce(func.sum(UserCard.quantity * Card.market_price), 0.0),
        func.coalesce(func.sum(UserCard.quantity), 0),
        func.count(func.distinct(UserCard.card_id)),
    ).join(Card, UserCard.card_id == Card.id).where(UserCard.user_id == user.id)

    result = await db.execute(stmt)
    total_value, cards_count, unique_cards = result.one()

    return PortfolioValueResponse(
        total_value=Decimal(total_value).quantize(Decimal("0.01")),
        cards_count=int(cards_count),
        unique_cards=int(unique_cards),
    )


@router.get("/{item_id}", response_model=CollectionItemResponse)
async def get_collection_item(
    item_id: int,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    stmt = (
        select(UserCard, Card)
        .join(Card, UserCard.card_id == Card.id)
        .where(UserCard.id == item_id, UserCard.user_id == user.id)
    )
    result = await db.execute(stmt)
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Collection item not found")
    uc, card = row

    return _item_response(uc, card)


@router.post("", response_model=CollectionItemResponse, status_code=201)
async def add_to_collection(
    body: CollectionAddRequest,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    card_stmt = select(Card).where(Card.id == body.card_id)
    card_result = await db.execute(card_stmt)
    card = card_result.scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")

    existing_stmt = select(UserCard).where(
        UserCard.user_id == user.id,
        UserCard.card_id == body.card_id,
        UserCard.condition == body.condition,
        UserCard.is_foil == body.is_foil,
        UserCard.language == body.language,
    )
    existing_result = await db.execute(existing_stmt)
    existing = existing_result.scalar_one_or_none()

    if existing is not None:
        existing.quantity += body.quantity
        if body.purchase_price is not None:
            existing.purchase_price = body.purchase_price
        existing.language = body.language
        await db.commit()
        await db.refresh(existing)
        uc = existing
    else:
        uc = UserCard(
            user_id=user.id,
            card_id=body.card_id,
            quantity=body.quantity,
            condition=body.condition,
            is_foil=body.is_foil,
            language=body.language,
            purchase_price=body.purchase_price,
        )
        db.add(uc)
        try:
            await db.commit()
        except IntegrityError:
            # Race: another request created the same variant between our
            # SELECT and INSERT. Roll back and merge into that row instead.
            await db.rollback()
            existing_result = await db.execute(existing_stmt)
            existing = existing_result.scalar_one_or_none()
            if existing is None:
                raise HTTPException(
                    status_code=409, detail="Conflict adding to collection"
                )
            existing.quantity += body.quantity
            if body.purchase_price is not None:
                existing.purchase_price = body.purchase_price
            existing.language = body.language
            await db.commit()
            await db.refresh(existing)
            uc = existing

    return _item_response(uc, card)


@router.post("/refresh-prices", status_code=202)
async def refresh_collection_prices(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    """Trigger a background market-price refresh of stale cards. Returns
    immediately (202); actual scraping runs in the background."""
    games_stmt = (
        select(func.distinct(Card.game))
        .select_from(UserCard)
        .join(Card, UserCard.card_id == Card.id)
        .where(UserCard.user_id == user.id)
    )
    result = await db.execute(games_stmt)
    game_values = [g for g in result.scalars().all() if g is not None]
    games = [g for g in game_values if Game(g) in SCRAPERS]

    asyncio.ensure_future(refresh_stale_prices())
    return {"status": "scheduled", "games": games}


@router.post("/{item_id}/split", response_model=CollectionItemResponse, status_code=201)
async def split_collection_item(
    item_id: int,
    body: CollectionSplitRequest,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    """Split copies off a grouped collection item into their own item.

    The source item is decremented and the split copies are merged into an
    existing item with the same (card, condition, foil, language) variant, or
    created as a new item — atomically in a single transaction. On a unique
    index race the transaction is rolled back and retried once.
    """

    async def _load_source() -> UserCard | None:
        result = await db.execute(
            select(UserCard).where(UserCard.id == item_id, UserCard.user_id == user.id)
        )
        return result.scalar_one_or_none()

    uc = await _load_source()
    if uc is None:
        raise HTTPException(status_code=404, detail="Collection item not found")
    if uc.quantity <= body.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot split: item has only {uc.quantity} copy(-ies)",
        )

    card_stmt = select(Card).where(Card.id == uc.card_id)
    card_result = await db.execute(card_stmt)
    card = card_result.scalar_one()

    # A separated copy must live in a different variant: the unique index
    # (user, card, condition, foil, language) forbids a second row with the
    # source's own variant.
    if (
        body.condition == uc.condition
        and body.is_foil == uc.is_foil
        and body.language == uc.language
    ):
        raise HTTPException(
            status_code=400,
            detail="Change the condition, foil or language to separate a copy",
        )

    variant_stmt = select(UserCard).where(
        UserCard.user_id == user.id,
        UserCard.card_id == uc.card_id,
        UserCard.condition == body.condition,
        UserCard.is_foil == body.is_foil,
        UserCard.language == body.language,
    )

    for _attempt in range(2):
        try:
            uc.quantity -= body.quantity
            if body.purchase_price is not None:
                uc.purchase_price = body.purchase_price
            target = (await db.execute(variant_stmt)).scalar_one_or_none()
            if target is not None:
                target.quantity += body.quantity
                await db.commit()
                await db.refresh(target)
                return _item_response(target, card)
            new_uc = UserCard(
                user_id=user.id,
                card_id=uc.card_id,
                quantity=body.quantity,
                condition=body.condition,
                is_foil=body.is_foil,
                language=body.language,
                purchase_price=body.purchase_price,
            )
            db.add(new_uc)
            await db.commit()
            await db.refresh(new_uc)
            return _item_response(new_uc, card)
        except IntegrityError:
            await db.rollback()
            uc = await _load_source()
            if uc is None:
                raise HTTPException(status_code=404, detail="Collection item not found")
            if uc.quantity <= body.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot split: item has only {uc.quantity} copy(-ies)",
                )

    raise HTTPException(status_code=409, detail="Concurrent split conflict; please retry")


@router.patch("/{item_id}", response_model=CollectionItemResponse)
async def update_collection_item(
    item_id: int,
    body: CollectionUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    stmt = select(UserCard).where(
        UserCard.id == item_id,
        UserCard.user_id == user.id,
    )
    result = await db.execute(stmt)
    uc = result.scalar_one_or_none()
    if uc is None:
        raise HTTPException(status_code=404, detail="Collection item not found")

    update_data = body.model_dump(exclude_unset=True)
    if update_data:
        try:
            update_stmt = (
                update(UserCard)
                .where(UserCard.id == item_id, UserCard.user_id == user.id)
                .values(**update_data)
            )
            await db.execute(update_stmt)
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=409,
                detail="An item with these card details already exists",
            )
        await db.refresh(uc)

    card_stmt = select(Card).where(Card.id == uc.card_id)
    card_result = await db.execute(card_stmt)
    card = card_result.scalar_one()

    return _item_response(uc, card)


@router.delete("/{item_id}", status_code=204)
async def delete_collection_item(
    item_id: int,
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    stmt = select(UserCard).where(
        UserCard.id == item_id,
        UserCard.user_id == user.id,
    )
    result = await db.execute(stmt)
    uc = result.scalar_one_or_none()
    if uc is None:
        raise HTTPException(status_code=404, detail="Collection item not found")

    await db.execute(delete(UserCard).where(UserCard.id == item_id))
    await db.commit()
