from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import current_user
from src.database import get_async_session
from src.models import Card, Condition, Game, User, UserCard
from src.schemas.collection import (
    CollectionAddRequest,
    CollectionItemResponse,
    CollectionListResult,
    CollectionUpdateRequest,
    PortfolioValueResponse,
)
from src.schemas.cards import CardResponse

router = APIRouter(prefix="/api/collection", tags=["collection"])


@router.get("", response_model=CollectionListResult)
async def list_collection(
    game: Game | None = Query(None, description="Filter by game"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    base_query = select(UserCard).where(UserCard.user_id == user.id)

    if game is not None:
        base_query = base_query.join(Card).where(Card.game == game)

    count_stmt = select(func.count()).select_from(base_query.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    pages = max(1, math.ceil(total / page_size))

    query = (
        base_query
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    enriched = []
    for uc in items:
        card_stmt = select(Card).where(Card.id == uc.card_id)
        card_result = await db.execute(card_stmt)
        card = card_result.scalar_one()
        enriched.append(CollectionItemResponse(
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
            total_value=round(uc.quantity * card.market_price, 2),
        ))

    return CollectionListResult(
        items=enriched,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.get("/value", response_model=PortfolioValueResponse)
async def portfolio_value(
    db: AsyncSession = Depends(get_async_session),
    user: User = Depends(current_user),
):
    stmt = select(
        func.coalesce(func.sum(UserCard.quantity * Card.market_price), 0.0),
        func.coalesce(func.sum(UserCard.quantity), 0),
        func.count(UserCard.id.distinct()),
    ).join(Card, UserCard.card_id == Card.id).where(UserCard.user_id == user.id)

    result = await db.execute(stmt)
    total_value, cards_count, unique_cards = result.one()

    return PortfolioValueResponse(
        total_value=round(float(total_value), 2),
        cards_count=int(cards_count),
        unique_cards=int(unique_cards),
    )


@router.get("/{item_id}", response_model=CollectionItemResponse)
async def get_collection_item(
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

    card_stmt = select(Card).where(Card.id == uc.card_id)
    card_result = await db.execute(card_stmt)
    card = card_result.scalar_one()

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
        total_value=round(uc.quantity * card.market_price, 2),
    )


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
        await db.commit()
        await db.refresh(uc)

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
        total_value=round(uc.quantity * card.market_price, 2),
    )


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
        update_stmt = (
            update(UserCard)
            .where(UserCard.id == item_id)
            .values(**update_data)
        )
        await db.execute(update_stmt)
        await db.commit()
        await db.refresh(uc)

    card_stmt = select(Card).where(Card.id == uc.card_id)
    card_result = await db.execute(card_stmt)
    card = card_result.scalar_one()

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
        total_value=round(uc.quantity * card.market_price, 2),
    )


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
