from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models import Card, Game
from src.scrapers.base import CardData
from src.scrapers.mtg import MtgScraper
from src.scrapers.pokemon import PokemonScraper
from src.scrapers.yugioh import YugiohScraper

SCRAPERS: dict[Game, Any] = {
    Game.MTG: MtgScraper,
    Game.POKEMON: PokemonScraper,
    Game.YUGIOH: YugiohScraper,
}

PRICE_TTL_HOURS = 24


def _get_scraper(game: Game):
    cls = SCRAPERS.get(game)
    if cls is None:
        raise ValueError(f"No scraper registered for game: {game}")
    return cls()


async def search_cards(db: AsyncSession, game: Game, query: str) -> list[Card]:
    stmt = (
        select(Card)
        .where(Card.game == game, Card.name.ilike(f"%{query}%"))
        .limit(50)
    )
    result = await db.execute(stmt)
    local_cards: list[Card] = list(result.scalars().all())

    expired = [
        c for c in local_cards
        if c.last_updated < datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=PRICE_TTL_HOURS)
    ]

    external_data: list[CardData] = []
    scraper = _get_scraper(game)
    try:
        external_data = await scraper.search(query)
    except Exception:
        external_data = []
    finally:
        await scraper.close()

    fresh_cards: list[Card] = []
    for data in external_data:
        card = await upsert_card(db, data)
        fresh_cards.append(card)

    if expired:
        for data in external_data:
            for old in expired:
                if old.set_code == data.set_code and old.collector_number == data.collector_number:
                    old.market_price = data.market_price
                    old.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
                    old.image_url = data.image_url
        await db.commit()

    await db.commit()
    return fresh_cards[:50]


async def refresh_card_price(db: AsyncSession, card: Card) -> float:
    scraper = _get_scraper(card.game)
    try:
        price = await scraper.get_price(f"{card.set_code}/{card.collector_number}")
    finally:
        await scraper.close()
    if price is not None:
        card.market_price = price
        card.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()
    return card.market_price


async def upsert_card(db: AsyncSession, data: CardData) -> Card:
    stmt = select(Card).where(
        Card.game == data.game,
        Card.set_code == data.set_code,
        Card.collector_number == data.collector_number,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        existing.name = data.name
        existing.set_name = data.set_name
        existing.rarity = data.rarity
        if data.image_url:
            existing.image_url = data.image_url
        if data.market_price > 0:
            existing.market_price = data.market_price
        existing.last_updated = datetime.now(timezone.utc).replace(tzinfo=None)
        existing.game_metadata = data.game_metadata
        return existing

    card = Card(
        game=data.game,
        name=data.name,
        set_name=data.set_name,
        set_code=data.set_code,
        collector_number=data.collector_number,
        rarity=data.rarity,
        image_url=data.image_url,
        market_price=data.market_price,
        last_updated=datetime.now(timezone.utc).replace(tzinfo=None),
        game_metadata=data.game_metadata,
    )
    db.add(card)
    await db.flush()
    return card


async def cli_search(game_name: str, query: str) -> None:
    game = Game(game_name)
    async with async_session_maker() as db:
        cards = await search_cards(db, game, query)
    if not cards:
        print("No cards found.")
        return
    print(f"\nFound {len(cards)} card(s):\n")
    for c in cards:
        name = c.name.encode("utf-8", errors="replace").decode("utf-8")
        set_name = c.set_name.encode("utf-8", errors="replace").decode("utf-8")
        print(f"  [{c.game}] {name} - {set_name} ({c.set_code}) #{c.collector_number}")
        print(f"         Price: ${c.market_price:.2f}  |  Rarity: {c.rarity}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="TrackerCG Scraper CLI")
    parser.add_argument("--game", required=True, help="Game code (e.g. MTG, POKEMON, YUGIOH)")
    parser.add_argument("--search", required=True, help="Card name to search")
    args = parser.parse_args()
    asyncio.run(cli_search(args.game.upper(), args.search))


if __name__ == "__main__":
    main()
