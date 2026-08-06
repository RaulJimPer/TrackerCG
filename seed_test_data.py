"""TrackerCG — seed test data.

Populates the local SQLite database with realistic test data for manual
UI testing. Deterministic: re-running FIRST wipes every table (user,
card, usercard) so the database always ends up in exactly the same
state — no leftover users, cards, or collection rows from previous runs.

Usage (from project root, venv active):
    venv\\Scripts\\python.exe seed_test_data.py

Requires the database schema to exist (run `alembic upgrade head` first
or let the app create it on first startup).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher
from sqlalchemy import delete, select

from src.database import async_engine, async_session_maker, create_db_and_tables
from src.models import Card, Condition, Game, User, UserCard

TEST_EMAILS = ("test@trackercg.dev", "second@trackercg.dev")
TEST_PASSWORD = "TestPass123"

password_hash = PasswordHash((Argon2Hasher(),))

# ---------------------------------------------------------------------------
# Card catalogue (name, game, set, set_code, number, rarity, image_url, price)
# ---------------------------------------------------------------------------
CARDS: list[tuple[str, Game, str, str, str, str, str, str]] = [
    # --- Magic: The Gathering (scraper available) ---
    ("Black Lotus", Game.MTG, "Alpha", "LEA", "232", "Rare", "https://cards.scryfall.io/large/front/b/0/b0faa7f2-b547-42c4-a810-839da50dadfe.jpg", "18450.00"),
    ("Ancestral Recall", Game.MTG, "Alpha", "LEA", "1", "Rare", "https://cards.scryfall.io/large/front/7/0/70e7ddf2-5604-41e7-bb9d-ddd03d3e9d0b.jpg", "12500.00"),
    ("Mox Sapphire", Game.MTG, "Alpha", "LEA", "260", "Rare", "https://cards.scryfall.io/large/front/8/2/82da0972-b17b-4600-9efd-e9430a0db04b.jpg", "6500.00"),
    ("Sol Ring", Game.MTG, "Commander 2011", "CMD", "178", "Uncommon", "https://cards.scryfall.io/large/front/7/1/71357a3d-9a9f-4ec6-8e01-1966b220206c.jpg", "35.50"),
    ("Lightning Bolt", Game.MTG, "Fourth Edition", "4ED", "185", "Common", "https://cards.scryfall.io/large/front/9/5/9521375e-0bc1-45ef-b513-6d332a25f9d2.jpg", "2.75"),
    ("Counterspell", Game.MTG, "Fourth Edition", "4ED", "63", "Common", "https://cards.scryfall.io/large/front/e/8/e8493631-6c9c-40a8-b7de-ecf26ba6bf7d.jpg", "1.20"),
    # --- Pokémon (scraper available) ---
    ("Charizard", Game.POKEMON, "Base Set", "BASE", "4", "Rare Holo", "https://images.tcggo.com/tcggo/storage/19322/conversions/charizard-b2-4-base-set-2-pokemon-large.webp", "350.00"),
    ("Blastoise", Game.POKEMON, "Base Set", "BASE", "2", "Rare Holo", "https://images.tcggo.com/tcggo/storage/19320/conversions/blastoise-b2-2-base-set-2-pokemon-large.webp", "180.00"),
    ("Umbreon VMAX", Game.POKEMON, "Evolving Skies", "EVS", "215", "Secret Rare", "https://images.tcggo.com/tcggo/storage/5506/conversions/umbreon-vmax-evs-215-evolving-skies-pokemon-large.webp", "1200.00"),
    ("Pikachu", Game.POKEMON, "Base Set", "BASE", "58", "Common", "https://images.tcggo.com/tcggo/storage/19405/conversions/pikachu-b2-87-base-set-2-pokemon-large.webp", "15.00"),
    ("Pikachu Illustrator", Game.POKEMON, "Corocoro Comic", "CRCR", "1", "Promo", "", "50000.00"),
    # --- Yu-Gi-Oh! (scraper available) ---
    ("Blue-Eyes White Dragon", Game.YUGIOH, "Legend of Blue Eyes", "LOB", "LOB-001", "Ultra Rare", "https://images.ygoprodeck.com/images/cards/89631139.jpg", "45.00"),
    ("Dark Magician", Game.YUGIOH, "Legend of Blue Eyes", "LOB", "LOB-005", "Ultra Rare", "https://images.ygoprodeck.com/images/cards/46986414.jpg", "35.00"),
    ("Exodia the Forbidden One", Game.YUGIOH, "Legend of Blue Eyes", "LOB", "LOB-124", "Secret Rare", "https://images.ygoprodeck.com/images/cards/33396948.jpg", "90.00"),
    # --- Riftbound (scraper available) ---
    ("Ahri, Alluring", Game.RIFTBOUND, "Origins", "OGN", "OGN-150", "Epic", "https://images.tcggo.com/tcggo/storage/33478/conversions/ahri-alluring-ogn-066298-origins-main-set-large.webp", "122.00"),
    ("Void Gate", Game.RIFTBOUND, "Origins", "OGN", "OGN-296", "Uncommon", "https://images.tcggo.com/tcggo/storage/33452/conversions/void-gate-large.webp", "0.50"),
    ("Bounty Hunter", Game.RIFTBOUND, "Origins", "OGN", "OGN-113", "Rare", "https://images.tcggo.com/tcggo/storage/33803/conversions/miss-fortune-bounty-hunter-ogn-267298-origins-main-set-large.webp", "116.53"),
]

# ---------------------------------------------------------------------------
# Collection entries for the main test user.
# (card_name, quantity, condition, is_foil, language, purchase_price)
# Ordered so that the most recently added (first in dashboard page 1)
# cover several games/conditions for filter and pagination testing.
# ---------------------------------------------------------------------------
COLLECTION: list[tuple[str, int, Condition, bool, str, str | None]] = [
    # page 1 (most recent -> varied games)
    ("Lightning Bolt", 4, Condition.NEAR_MINT, False, "EN", "1.50"),
    ("Charizard", 1, Condition.NEAR_MINT, False, "EN", "320.00"),
    ("Blue-Eyes White Dragon", 2, Condition.NEAR_MINT, False, "EN", "40.00"),
    ("Ahri, Alluring", 1, Condition.NEAR_MINT, False, "EN", "110.00"),
    ("Sol Ring", 3, Condition.LIGHTLY_PLAYED, False, "EN", "28.00"),
    ("Pikachu", 5, Condition.NEAR_MINT, False, "EN", "12.00"),
    ("Dark Magician", 3, Condition.LIGHTLY_PLAYED, False, "EN", "30.00"),
    ("Void Gate", 2, Condition.NEAR_MINT, False, "EN", "0.30"),
    ("Charizard", 1, Condition.MINT, True, "EN", "360.00"),
    ("Umbreon VMAX", 1, Condition.NEAR_MINT, True, "EN", "1150.00"),
    ("Exodia the Forbidden One", 1, Condition.NEAR_MINT, False, "EN", "85.00"),
    ("Bounty Hunter", 2, Condition.NEAR_MINT, False, "EN", "100.00"),
    ("Black Lotus", 1, Condition.LIGHTLY_PLAYED, False, "EN", "16500.00"),
    ("Blastoise", 2, Condition.LIGHTLY_PLAYED, False, "EN", "150.00"),
    ("Ancestral Recall", 1, Condition.NEAR_MINT, False, "EN", "12000.00"),
    ("Mox Sapphire", 1, Condition.NEAR_MINT, False, "EN", "6100.00"),
    ("Counterspell", 4, Condition.NEAR_MINT, False, "ES", "0.80"),
    ("Pikachu Illustrator", 1, Condition.NEAR_MINT, False, "EN", "49000.00"),
    ("Blue-Eyes White Dragon", 1, Condition.MINT, True, "JP", "60.00"),
    ("Dark Magician", 1, Condition.NEAR_MINT, True, "EN", "45.00"),
    # page 2 (older entries -> MTG heavy)
    ("Sol Ring", 2, Condition.NEAR_MINT, False, "EN", "33.00"),
    ("Lightning Bolt", 6, Condition.PLAYED, False, "EN", "1.00"),
    ("Charizard", 1, Condition.PLAYED, False, "EN", "250.00"),
    ("Pikachu", 3, Condition.LIGHTLY_PLAYED, False, "FR", "10.00"),
    ("Ahri, Alluring", 1, Condition.LIGHTLY_PLAYED, True, "EN", "95.00"),
    ("Void Gate", 1, Condition.PLAYED, False, "EN", "0.20"),
    ("Exodia the Forbidden One", 1, Condition.LIGHTLY_PLAYED, False, "EN", "75.00"),
    ("Blastoise", 1, Condition.NEAR_MINT, True, "EN", "200.00"),
    ("Mox Sapphire", 1, Condition.PLAYED, False, "EN", "5200.00"),
    ("Counterspell", 2, Condition.LIGHTLY_PLAYED, False, "EN", "0.60"),
]

# Collection for the second user (small, single game — isolation test).
COLLECTION_SECOND: list[tuple[str, int, Condition, bool, str, str | None]] = [
    ("Pikachu", 1, Condition.NEAR_MINT, False, "EN", "14.00"),
    ("Void Gate", 1, Condition.NEAR_MINT, False, "EN", "0.40"),
]

CONDITIONS = {
    "Mint": Condition.MINT,
    "Near Mint": Condition.NEAR_MINT,
    "Lightly Played": Condition.LIGHTLY_PLAYED,
    "Played": Condition.PLAYED,
    "Damaged": Condition.DAMAGED,
}


async def wipe_all_data(db) -> None:
    """Delete ALL existing rows so the reseeded database is deterministic.

    Runs before any insert. With the PRAGMA foreign_keys=ON listener the
    CASCADE FKs would cascade usercard rows anyway, but deleting children
    first keeps the script safe even without FK enforcement.
    """
    await db.execute(delete(UserCard))
    await db.execute(delete(Card))
    await db.execute(delete(User))
    await db.commit()


async def get_or_create_user(db, email: str) -> User:
    existing = (
        await db.execute(select(User).where(User.email == email))
    ).scalar_one_or_none()
    if existing is not None:
        return existing
    hashed = password_hash.hash(TEST_PASSWORD)
    user = User(
        email=email,
        hashed_password=hashed,
        is_active=True,
        is_superuser=False,
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    return user


async def seed() -> None:
    await create_db_and_tables()
    async with async_session_maker() as db:
        await wipe_all_data(db)

        # --- Users ---
        main_user = await get_or_create_user(db, TEST_EMAILS[0])
        second_user = await get_or_create_user(db, TEST_EMAILS[1])

        # --- Cards (external_id = seed-{index}; image_url '' kept as-is) ---
        card_rows: dict[str, Card] = {}
        now = datetime.now(timezone.utc)
        for i, (name, game, set_name, set_code, number, rarity, image_url, price) in enumerate(CARDS):
            card = Card(
                game=game,
                external_id=f"seed-{i}",
                name=name,
                set_name=set_name,
                set_code=set_code,
                collector_number=number,
                rarity=rarity,
                image_url=image_url,
                market_price=Decimal(price),
                last_updated=now - timedelta(days=2),
                game_metadata={"source": "seed", "note": "manual test fixture"},
            )
            db.add(card)
            await db.flush()
            card_rows[name] = card

        # --- Main user collection (added_at staggered, newest first) ---
        base = now - timedelta(hours=1)
        for i, (name, qty, cond, foil, lang, purchase) in enumerate(COLLECTION):
            card = card_rows[name]
            db.add(
                UserCard(
                    user_id=main_user.id,
                    card_id=card.id,
                    quantity=qty,
                    condition=cond,
                    is_foil=foil,
                    language=lang,
                    purchase_price=Decimal(purchase) if purchase else None,
                    added_at=base - timedelta(minutes=5 * i),
                )
            )

        # --- Second user collection ---
        for i, (name, qty, cond, foil, lang, purchase) in enumerate(COLLECTION_SECOND):
            card = card_rows[name]
            db.add(
                UserCard(
                    user_id=second_user.id,
                    card_id=card.id,
                    quantity=qty,
                    condition=cond,
                    is_foil=foil,
                    language=lang,
                    purchase_price=Decimal(purchase) if purchase else None,
                    added_at=base - timedelta(minutes=5 * i),
                )
            )

        await db.commit()

        # --- Summary ---
        print("Database wiped (user, card, usercard).")
        print(f"Users created: {len(TEST_EMAILS)}")
        for email in TEST_EMAILS:
            print(f"  -> {email} / {TEST_PASSWORD}")
        print(f"Cards inserted: {len(CARDS)}")
        print(f"Main collection items: {len(COLLECTION)}  (page 1=20, page 2={len(COLLECTION)-20})")
        print(f"Second collection items: {len(COLLECTION_SECOND)}")
        print("\nDone. Start the server and log in as test@trackercg.dev / TestPass123")


async def main() -> None:
    await seed()
    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
