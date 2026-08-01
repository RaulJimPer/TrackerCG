"""Card endpoints: search, detail, refresh-price."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from src.models import Game
from test.conftest import auth_headers, create_card, login, register_user


async def test_search_requires_auth(client):
    r = await client.get("/api/cards/search", params={"q": "blue"})
    assert r.status_code == 401


async def test_search_mixed_fresh_and_stale_returns_all(client, session_maker):
    # A stale match (game without scraper) must not be hidden when another
    # game has fresh matches for the same query (regression: fresh-only return
    # used to drop Elsa because "Gaius van Baelsar" also matches "%elsa%").
    stale = datetime.now(timezone.utc) - timedelta(days=2)
    await create_card(
        session_maker,
        name="Elsa, Spirit of Winter",
        game=Game.LORCANA,
        last_updated=stale,
    )
    await create_card(
        session_maker,
        name="Gaius van Baelsar",
        game=Game.MTG,
        external_id="uuid-elsa-match",
    )
    await register_user(client)
    token = await login(client)
    r = await client.get(
        "/api/cards/search",
        params={"q": "elsa"},
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    names = {item["name"] for item in body["items"]}
    assert "Elsa, Spirit of Winter" in names
    assert "Gaius van Baelsar" in names


async def test_search_local_finds_card(client, session_maker):
    await create_card(session_maker, name="Blue-Eyes White Dragon", game=Game.YUGIOH)
    await register_user(client)
    token = await login(client)
    r = await client.get(
        "/api/cards/search",
        params={"q": "blue", "game": "YUGIOH"},
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Blue-Eyes White Dragon"


async def test_search_no_scraper_game_ok(client, session_maker):
    # Lorcana has no scraper: local results only, no 422/500.
    await create_card(session_maker, name="Elsa", game=Game.LORCANA)
    await register_user(client)
    token = await login(client)
    r = await client.get(
        "/api/cards/search",
        params={"q": "elsa", "game": "LORCANA"},
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    assert r.json()["total"] == 1


async def test_search_unknown_game_422(client):
    await register_user(client)
    token = await login(client)
    r = await client.get(
        "/api/cards/search",
        params={"q": "blue", "game": "NOTAGAME"},
        headers=auth_headers(token),
    )
    assert r.status_code == 422


async def test_search_empty_db(client):
    await register_user(client)
    token = await login(client)
    r = await client.get(
        "/api/cards/search",
        params={"q": "zzz"},
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_get_card_requires_auth(client, session_maker):
    card = await create_card(session_maker)
    r = await client.get(f"/api/cards/{card.id}")
    assert r.status_code == 401


async def test_get_card_ok(client, session_maker):
    card = await create_card(session_maker, market_price=Decimal("12.34"))
    await register_user(client)
    token = await login(client)
    r = await client.get(f"/api/cards/{card.id}", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["market_price"] == "12.34"


async def test_get_card_not_found(client):
    await register_user(client)
    token = await login(client)
    r = await client.get("/api/cards/999999", headers=auth_headers(token))
    assert r.status_code == 404


async def test_refresh_price_no_scraper_game_400(client, session_maker):
    card = await create_card(session_maker, game=Game.LORCANA)
    await register_user(client)
    token = await login(client)
    r = await client.post(
        f"/api/cards/{card.id}/refresh-price",
        headers=auth_headers(token),
    )
    assert r.status_code == 400
    assert "No price source available" in r.json()["detail"]


async def test_refresh_price_not_found_404(client):
    await register_user(client)
    token = await login(client)
    r = await client.post(
        "/api/cards/999999/refresh-price",
        headers=auth_headers(token),
    )
    assert r.status_code == 404


async def test_refresh_price_requires_auth(client, session_maker):
    card = await create_card(session_maker)
    r = await client.post(f"/api/cards/{card.id}/refresh-price")
    assert r.status_code == 401
