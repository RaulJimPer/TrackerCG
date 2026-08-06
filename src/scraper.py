from __future__ import annotations

import argparse
import asyncio
import logging
import random
import sys
import threading
from datetime import datetime, timedelta, timezone
from decimal import Decimal

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import async_session_maker
from src.models import Card, Game
from src.scrapers.base import CardData, ScraperBase
from src.scrapers.mtg import MtgScraper
from src.scrapers.pokemon import PokemonScraper
from src.scrapers.riftbound import RiftboundScraper
from src.scrapers.yugioh import YugiohScraper

logger = logging.getLogger(__name__)

SCRAPERS: dict[Game, type[ScraperBase]] = {
    Game.MTG: MtgScraper,
    Game.POKEMON: PokemonScraper,
    Game.YUGIOH: YugiohScraper,
    Game.RIFTBOUND: RiftboundScraper,
}

PRICE_TTL_HOURS = 24

_instances: dict[Game, ScraperBase] = {}
_instances_lock = threading.Lock()
_in_flight: dict[tuple[str, str], asyncio.Future[None]] = {}
_background_tasks: set[asyncio.Task] = set()
_stale_refresh_running = False
_stale_refresh_in_flight: asyncio.Task | None = None


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
    """Close all pooled scraper clients (httpx)."""
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
    try:
        scraper = get_scraper(game)
    except Exception:
        logger.warning("No scraper available for %s; skipping external search", game.value)
        return
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


def _search_key(game: Game | None, query: str) -> tuple[str, str]:
    return (game.value if game is not None else "*", query.strip().lower())


async def _refresh_external(games: list[Game], query: str) -> None:
    await asyncio.gather(
        *(_search_game_external(g, query) for g in games),
        return_exceptions=True,
    )


async def _run_single_flight(key: tuple[str, str], games: list[Game], query: str) -> None:
    """Run an external refresh guarded by the single-flight map."""
    task = asyncio.ensure_future(_refresh_external(games, query))
    _in_flight[key] = task
    try:
        await task
    finally:
        _in_flight.pop(key, None)


def _spawn_background(games: list[Game], query: str) -> None:
    """Fire-and-forget external refresh. Never blocks or raises."""
    games = [g for g in games if g in SCRAPERS]
    if not games:
        return

    async def _run() -> None:
        try:
            await _refresh_external(games, query)
        except Exception:
            logger.exception("Background refresh failed (query=%r)", query)

    task = asyncio.ensure_future(_run())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def search_cards(
    db: AsyncSession,
    game: Game | None,
    query: str,
) -> list[Card]:
    """Cache-first search.

    Every local match is returned immediately — fresh or stale — so the user
    never waits for scraping and stale local matches stay visible. An external
    refresh is only spawned when nothing local is fresh, and only when there
    are no local matches at all do we wait for the single-flight background
    refresh so newly-scraped cards can be returned.
    """
    local = await _local_matches(db, game, query)
    now = _utcnow()
    ttl = timedelta(hours=PRICE_TTL_HOURS)
    fresh = [c for c in local if c.last_updated >= now - ttl]

    if local:
        if not fresh:
            games = [g for g in (list(SCRAPERS) if game is None else [game]) if g in SCRAPERS]
            _spawn_background(games, query)
        return local[:50]

    games = [g for g in (list(SCRAPERS) if game is None else [game]) if g in SCRAPERS]
    if not games:
        return []

    key = _search_key(game, query)
    if key not in _in_flight:
        await _run_single_flight(key, games, query)
    else:
        await _in_flight[key]

    return (await _local_matches(db, game, query))[:50]


async def refresh_stale_prices(limit: int = 25) -> int:
    """Refresh market prices of stale cards (older than TTL) in the background.

    Only touches cards whose game has a registered scraper. Returns the number
    of cards successfully refreshed. One AsyncSession per card, random 1-3s
    delay between requests to be kind to upstream sources.

    Single-flight: concurrent callers (periodic task + user-triggered refresh)
    do not duplicate work — the first caller refreshes and the rest return 0.
    """
    global _stale_refresh_running
    if _stale_refresh_running:
        return 0
    _stale_refresh_running = True
    try:
        cutoff = _utcnow() - timedelta(hours=PRICE_TTL_HOURS)
        async with async_session_maker() as db:
            stmt = (
                select(Card)
                .where(Card.last_updated < cutoff)
                .order_by(Card.last_updated)
                .limit(limit)
            )
            result = await db.execute(stmt)
            cards = list(result.scalars().all())

        refreshed = 0
        for card in cards:
            if card.game not in SCRAPERS:
                continue
            try:
                async with async_session_maker() as db:
                    fresh_card = await db.get(Card, card.id)
                    if fresh_card is None:
                        continue
                    price = await get_scraper(fresh_card.game).get_price(
                        fresh_card.external_id or f"{fresh_card.set_code}/{fresh_card.collector_number}"
                    )
                    if price is not None and price > 0:
                        fresh_card.market_price = price
                        fresh_card.last_updated = _utcnow()
                        await db.commit()
                        refreshed += 1
            except Exception:
                logger.exception("Stale price refresh failed for card %s", card.id)
            await asyncio.sleep(random.uniform(1, 3))

        if refreshed:
            logger.info("Refreshed prices for %d stale card(s)", refreshed)
        return refreshed
    finally:
        _stale_refresh_running = False


def spawn_stale_price_refresh(limit: int = 25) -> bool:
    """Schedule a tracked background refresh of stale card prices.

    Fire-and-forget for route handlers, but single-flight: if a refresh is
    already running (periodic task or a previous request), no new task is
    spawned. Returns True when a new task was scheduled, False otherwise.
    """
    global _stale_refresh_in_flight
    if _stale_refresh_in_flight is not None and not _stale_refresh_in_flight.done():
        return False

    async def _run() -> None:
        try:
            await refresh_stale_prices(limit)
        except Exception:
            logger.exception("Background stale-price refresh failed")

    task = asyncio.ensure_future(_run())
    _stale_refresh_in_flight = task
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return True


async def refresh_card_price(db: AsyncSession, card: Card) -> Decimal:
    if card.game not in SCRAPERS:
        return card.market_price
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
    parser.add_argument(
        "--game", required=True, help="Game code (e.g. MTG, POKEMON, YUGIOH, RIFTBOUND)"
    )
    parser.add_argument("--search", required=True, help="Card name to search")
    args = parser.parse_args()
    asyncio.run(cli_search(args.game.upper(), args.search))


if __name__ == "__main__":
    main()
