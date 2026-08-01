"""Shared pytest fixtures for TrackerCG.

Every test gets a fresh temporary SQLite database and a fresh httpx client
that talks to the real FastAPI app (ASGITransport) with all middleware active.
Rate-limit storage is reset between tests so counters never leak across cases.
External scraping is neutralized (no network) by patching the background
refresh entry points in src.scraper.
"""
from __future__ import annotations

from decimal import Decimal

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from src.models import Card, Game
from src.rate_limit import limiter

TEST_PASSWORD = "ValidPass1"


async def _noop_background(games: list, query: str) -> None:
    return None


async def _noop_single_flight(key: tuple, games: list, query: str) -> None:
    return None


@pytest.fixture(autouse=True)
def _no_external_scraping(monkeypatch):
    """Never hit external markets during tests; background refreshes no-op."""
    monkeypatch.setattr("src.scraper._spawn_background", _noop_background)
    monkeypatch.setattr("src.scraper._run_single_flight", _noop_single_flight)


@pytest.fixture
async def session_maker(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    monkeypatch.setattr("src.database.async_engine", engine)
    monkeypatch.setattr("src.database.async_session_maker", maker)
    monkeypatch.setattr("src.scraper.async_session_maker", maker)

    limiter.reset()
    yield maker
    limiter.reset()
    await engine.dispose()


@pytest.fixture
async def client(session_maker):
    from src.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


async def register_user(client, email: str = "user@trackercg.dev", password: str = TEST_PASSWORD) -> int:
    r = await client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return r.status_code


async def login(client, email: str = "user@trackercg.dev", password: str = TEST_PASSWORD) -> str:
    r = await client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 204, r.text
    cookie = r.headers.get("set-cookie", "")
    assert "trackercg_session=" in cookie
    return cookie.split(";")[0].split("=", 1)[1]


def auth_headers(token: str) -> dict[str, str]:
    return {"Cookie": f"trackercg_session={token}"}


async def create_card(session_maker, **overrides) -> Card:
    """Insert a card row directly in the test DB (no scraping involved)."""
    defaults = dict(
        game=Game.MTG,
        external_id="seed-test-1",
        name="Test Card",
        set_name="Test Set",
        set_code="TST",
        collector_number="1",
        rarity="Common",
        image_url="",
        market_price=Decimal("10.00"),
    )
    defaults.update(overrides)
    async with session_maker() as db:
        card = Card(**defaults)
        db.add(card)
        await db.commit()
        await db.refresh(card)
        return card


async def add_to_collection(client, token: str, card_id: int, quantity: int = 1, **overrides) -> dict:
    body = {"card_id": card_id, "quantity": quantity}
    body.update(overrides)
    r = await client.post("/api/collection", json=body, headers=auth_headers(token))
    assert r.status_code == 201, r.text
    return r.json()
