from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models import Card, Game
from src.scrapers.base import CardData, ScraperBase
from src.scrapers.mtg import MtgScraper
from src.scrapers.pokemon import PokemonScraper
from src.scrapers.yugioh import YugiohScraper

logger = logging.getLogger(__name__)

SCRAPERS: dict[Game, type[ScraperBase]] = {
    Game.MTG: MtgScraper,
    Game.POKEMON: PokemonScraper,
    Game.YUGIOH: YugiohScraper,
}

PRICE_TTL_HOURS = 24

_instances: dict[Game, ScraperBase] = {}
_instances_lock = threading.Lock()
_in_flight: dict[tuple[str, str], asyncio.Future[None]] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_scraper(game: Game) -> ScraperBase:
    """Return the process-wide singleton scraper instance for a game."""
    instance = _instances.get(game)
    if instance is not None:
        return instance

    cls = SCRAPERS.get(game)
    if cls is None:
        raise ValueError(f"No scraper registered for game: {game}")

    with _instances_lock:
        instance = _instances.get(game)
        if instance is None:
            instance = cls()
            _instances[game] = instance
    return instance


async def close_scrapers() -> None:
    """Close all pooled clients and the shared Playwright browser."""
    for game, scraper in list(_instances.items()):
        try:
            await scraper.close()
        except Exception:
            logger.exception("Error closing scraper for %s", game)
    _instances.clear()


def _card_identity_stmt(data: CardData):
    if data.external_id:
        return select(Card).where(
            Card.game == data.game,
            Card.external_id == data.external_id,
        )
    return select(Card).where(
        Card.game == data.game,
        Card.set_code == data.set_code,
        Card.collector_number == data.collector_number,
    )


async def upsert_card(db: AsyncSession, data: CardData) -> Card:
    result = await db.execute(_card_identity_stmt(data))
    existing = result.scalar_one_or_none()

    if existing is not None:
        if data.external_id:
            existing.external_id = data.external_id
        existing.name = data.name
        existing.set_name = data.set_name
        existing.rarity = data.rarity
        if data.image_url:
            existing.image_url = data.image_url
        if data.market_price > 0:
            existing.market_price = data.market_price
        existing.last_updated = _utcnow()
        existing.game_metadata = data.game_metadata
        return existing

    card = Card(
        game=data.game,
        external_id=data.external_id,
        name=data.name,
        set_name=data.set_name,
        set_code=data.set_code,
        collector_number=data.collector_number,
        rarity=data.rarity,
        image_url=data.image_url,
        market_price=data.market_price,
        last_updated=_utcnow(),
        game_metadata=data.game_metadata,
    )
    db.add(card)
    await db.flush()
    return card


async def _search_game_external(game: Game, query: str) -> None:
    """Scrape one game's source and upsert results in its own session.
    Failures degrade to local-only."""
    scraper = get_scraper(game)
    try:
        data = await scraper.search(query)
    except Exception:
        logger.exception("External search failed for %s (query=%r)", game.value, query)
        return
    try:
        async with async_session_maker() as db:
            for item in data:
                await upsert_card(db, item)
            await db.commit()
    except Exception:
        logger.exception("Upsert failed for %s (query=%r)", game.value, query)


async def _local_matches(db: AsyncSession, game: Game | None, query: str) -> list[Card]:
    stmt = select(Card).where(Card.name.ilike(f"%{query}%"))
    if game is not None:
        stmt = stmt.where(Card.game == game)
    stmt = stmt.order_by(Card.game, Card.name, Card.id).limit(100)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def search_cards(
    db: AsyncSession,
    game: Game | None,
    query: str,
) -> list[Card]:
    """Cache-first search. Fresh local results are served immediately; stale or
    missing results trigger a single-flight external fetch across the requested
    games (all supported games when ``game`` is None)."""
    local = await _local_matches(db, game, query)
    now = _utcnow()
    ttl = timedelta(hours=PRICE_TTL_HOURS)
    fresh = [c for c in local if c.last_updated >= now - ttl]

    if fresh:
        return fresh[:50]

    key = (game.value if game is not None else "*", query.strip().lower())
    in_progress = _in_flight.get(key)
    if in_progress is None:
        games = list(SCRAPERS) if game is None else [game]

        async def _run() -> None:
            await asyncio.gather(
                *(_search_game_external(g, query) for g in games),
                return_exceptions=True,
            )

        task = asyncio.ensure_future(_run())
        _in_flight[key] = task
        try:
            await task
        finally:
            _in_flight.pop(key, None)
    else:
        await in_progress

    return (await _local_matches(db, game, query))[:50]


async def refresh_card_price(db: AsyncSession, card: Card) -> Decimal:
    scraper = get_scraper(card.game)
    ref = card.external_id or f"{card.set_code}/{card.collector_number}"
    try:
        price = await scraper.get_price(ref)
    except Exception:
        logger.exception("Price refresh failed for card %s (ref=%r)", card.id, ref)
        price = None
    if price is not None:
        card.market_price = price
        card.last_updated = _utcnow()
        await db.commit()
    return card.market_price


async def cli_search(game_name: str, query: str) -> None:
    game = Game(game_name)
    async with async_session_maker() as db:
        cards = await search_cards(db, game, query)
    await close_scrapers()
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
