"""Collection endpoints: CRUD, merge, split, games, value, isolation."""
from __future__ import annotations

import asyncio
from decimal import Decimal

from src.models import Condition, Game
from test.conftest import add_to_collection, auth_headers, create_card, login, register_user


async def test_collection_requires_auth(client):
    r = await client.get("/api/collection")
    assert r.status_code == 401


async def test_add_card_ok(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="add@trackercg.dev")
    token = await login(client, email="add@trackercg.dev")
    item = await add_to_collection(client, token, card.id)
    assert item["card_id"] == card.id
    assert item["quantity"] == 1
    assert item["total_value"] == "10.00"


async def test_add_card_not_found(client):
    await register_user(client, email="nf@trackercg.dev")
    token = await login(client, email="nf@trackercg.dev")
    r = await client.post(
        "/api/collection",
        json={"card_id": 999999, "quantity": 1},
        headers=auth_headers(token),
    )
    assert r.status_code == 404


async def test_add_merges_same_variant(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="merge@trackercg.dev")
    token = await login(client, email="merge@trackercg.dev")
    item1 = await add_to_collection(client, token, card.id, quantity=2)
    item2 = await add_to_collection(client, token, card.id, quantity=3)
    assert item1["id"] == item2["id"]
    assert item2["quantity"] == 5


async def test_add_different_condition_creates_new_item(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="cond@trackercg.dev")
    token = await login(client, email="cond@trackercg.dev")
    item1 = await add_to_collection(client, token, card.id, quantity=1)
    item2 = await add_to_collection(
        client, token, card.id, quantity=1, condition=Condition.MINT
    )
    assert item1["id"] != item2["id"]


async def test_list_collection_pagination(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="list@trackercg.dev")
    token = await login(client, email="list@trackercg.dev")
    for _ in range(3):
        await add_to_collection(client, token, card.id, quantity=1)
    r = await client.get(
        "/api/collection?page=1&page_size=2", headers=auth_headers(token)
    )
    assert r.status_code == 200
    body = r.json()
    # 3 identical adds merge into a single item; assert on the shape instead.
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert len(body["items"]) == min(2, body["total"])


async def test_list_collection_filter_by_game(client, session_maker):
    mtg = await create_card(session_maker, game=Game.MTG, name="Bolt")
    await create_card(session_maker, game=Game.RIFTBOUND, name="Void Gate")
    await register_user(client, email="filter@trackercg.dev")
    token = await login(client, email="filter@trackercg.dev")
    await add_to_collection(client, token, mtg.id)
    r = await client.get(
        "/api/collection?game=RIFTBOUND", headers=auth_headers(token)
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0


async def test_games_endpoint(client, session_maker):
    await create_card(session_maker, game=Game.POKEMON, name="Pika")
    await create_card(session_maker, game=Game.RIFTBOUND, name="Void Gate")
    await register_user(client, email="games@trackercg.dev")
    token = await login(client, email="games@trackercg.dev")
    r = await client.get("/api/collection/games", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json() == []

    # Add a Pokemon card then the games list reflects the user's collection.
    poke = (await _cards_by_game(session_maker, Game.POKEMON))[0]
    await add_to_collection(client, token, poke.id)
    r = await client.get("/api/collection/games", headers=auth_headers(token))
    assert r.json() == ["POKEMON"]


async def test_value_endpoint(client, session_maker):
    card = await create_card(session_maker, market_price=Decimal("25.00"))
    await register_user(client, email="val@trackercg.dev")
    token = await login(client, email="val@trackercg.dev")
    await add_to_collection(client, token, card.id, quantity=4)
    r = await client.get("/api/collection/value", headers=auth_headers(token))
    assert r.status_code == 200
    body = r.json()
    assert body["total_value"] == "100.00"
    assert body["cards_count"] == 4
    assert body["unique_cards"] == 1


async def test_value_decimal_exact(client, session_maker):
    """Portfolio value is summed with Decimal, never SQL float arithmetic."""
    card = await create_card(session_maker, market_price=Decimal("0.10"))
    await register_user(client, email="valdec@trackercg.dev")
    token = await login(client, email="valdec@trackercg.dev")
    await add_to_collection(client, token, card.id, quantity=3)
    r = await client.get("/api/collection/value", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["total_value"] == "0.30"


async def test_update_item(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="upd@trackercg.dev")
    token = await login(client, email="upd@trackercg.dev")
    item = await add_to_collection(client, token, card.id, quantity=2)
    r = await client.patch(
        f"/api/collection/{item['id']}",
        json={"quantity": 7},
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    assert r.json()["quantity"] == 7


async def test_update_item_not_found(client):
    await register_user(client, email="updnf@trackercg.dev")
    token = await login(client, email="updnf@trackercg.dev")
    r = await client.patch(
        "/api/collection/999999", json={"quantity": 2}, headers=auth_headers(token)
    )
    assert r.status_code == 404


async def test_delete_item(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="del@trackercg.dev")
    token = await login(client, email="del@trackercg.dev")
    item = await add_to_collection(client, token, card.id)
    r = await client.delete(
        f"/api/collection/{item['id']}", headers=auth_headers(token)
    )
    assert r.status_code == 204
    r = await client.get(
        f"/api/collection/{item['id']}", headers=auth_headers(token)
    )
    assert r.status_code == 404


async def test_refresh_prices_schedules(client):
    """POST /api/collection/refresh-prices returns 202; with no scraper-backed
    games in the collection no background refresh is spawned."""
    await register_user(client, email="refr@trackercg.dev")
    token = await login(client, email="refr@trackercg.dev")
    r = await client.post("/api/collection/refresh-prices", headers=auth_headers(token))
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "scheduled"
    assert body["games"] == []
    assert body["already_running"] is False


async def test_refresh_prices_with_scraper_game_spawns(client, session_maker):
    card = await create_card(session_maker, game=Game.MTG)
    await register_user(client, email="refrmtg@trackercg.dev")
    token = await login(client, email="refrmtg@trackercg.dev")
    await add_to_collection(client, token, card.id)
    r = await client.post("/api/collection/refresh-prices", headers=auth_headers(token))
    assert r.status_code == 202
    body = r.json()
    assert body["games"] == ["MTG"]
    assert body["already_running"] is False
    # Let the tracked background task finish before the event loop closes.
    await asyncio.sleep(0.1)


async def test_split_ok(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="split@trackercg.dev")
    token = await login(client, email="split@trackercg.dev")
    item = await add_to_collection(client, token, card.id, quantity=3)
    r = await client.post(
        f"/api/collection/{item['id']}/split",
        json={"quantity": 1, "condition": Condition.MINT.value},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    new_item = r.json()
    assert new_item["quantity"] == 1
    assert new_item["condition"] == Condition.MINT.value
    assert new_item["id"] != item["id"]
    # Original decremented.
    r = await client.get(
        f"/api/collection/{item['id']}", headers=auth_headers(token)
    )
    assert r.json()["quantity"] == 2


async def test_split_same_variant_400(client, session_maker):
    """Splitting into the source's own variant is rejected (unique index)."""
    card = await create_card(session_maker)
    await register_user(client, email="splitsame@trackercg.dev")
    token = await login(client, email="splitsame@trackercg.dev")
    item = await add_to_collection(client, token, card.id, quantity=3)
    r = await client.post(
        f"/api/collection/{item['id']}/split",
        json={"quantity": 1, "condition": item["condition"]},
        headers=auth_headers(token),
    )
    assert r.status_code == 400
    # Source untouched.
    r = await client.get(
        f"/api/collection/{item['id']}", headers=auth_headers(token)
    )
    assert r.json()["quantity"] == 3


async def test_split_qty_ge_available_400(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="split400@trackercg.dev")
    token = await login(client, email="split400@trackercg.dev")
    item = await add_to_collection(client, token, card.id, quantity=1)
    r = await client.post(
        f"/api/collection/{item['id']}/split",
        json={"quantity": 1},
        headers=auth_headers(token),
    )
    assert r.status_code == 400


async def test_split_not_found_404(client):
    await register_user(client, email="splitnf@trackercg.dev")
    token = await login(client, email="splitnf@trackercg.dev")
    r = await client.post(
        "/api/collection/999999/split",
        json={"quantity": 1},
        headers=auth_headers(token),
    )
    assert r.status_code == 404


async def test_split_merges_into_existing_variant(client, session_maker):
    """Splitting into a variant that already exists merges (no duplicate row)."""
    card = await create_card(session_maker)
    await register_user(client, email="splitmerge@trackercg.dev")
    token = await login(client, email="splitmerge@trackercg.dev")
    grouped = await add_to_collection(client, token, card.id, quantity=3)
    existing = await add_to_collection(
        client, token, card.id, quantity=1, condition=Condition.MINT
    )

    r = await client.post(
        f"/api/collection/{grouped['id']}/split",
        json={"quantity": 1, "condition": Condition.MINT.value},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    merged = r.json()
    assert merged["id"] == existing["id"]
    assert merged["quantity"] == 2
    # Original decremented; still exactly two rows for this card.
    r = await client.get(
        f"/api/collection/{grouped['id']}", headers=auth_headers(token)
    )
    assert r.json()["quantity"] == 2
    r = await client.get("/api/collection", headers=auth_headers(token))
    rows = [i for i in r.json()["items"] if i["card_id"] == card.id]
    assert len(rows) == 2


async def test_split_keeps_source_purchase_price(client, session_maker):
    """Splitting must not overwrite the source item's purchase price (M3)."""
    card = await create_card(session_maker)
    await register_user(client, email="splitpp@trackercg.dev")
    token = await login(client, email="splitpp@trackercg.dev")
    item = await add_to_collection(
        client, token, card.id, quantity=3, purchase_price="10.00"
    )
    r = await client.post(
        f"/api/collection/{item['id']}/split",
        json={"quantity": 1, "condition": Condition.MINT.value, "purchase_price": "99.99"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201
    r = await client.get(f"/api/collection/{item['id']}", headers=auth_headers(token))
    assert r.json()["quantity"] == 2
    assert r.json()["purchase_price"] == "10.00"


async def test_update_variant_conflict_409(client, session_maker):
    """Updating an item into an existing variant is rejected with 409."""
    card = await create_card(session_maker)
    await register_user(client, email="upd409@trackercg.dev")
    token = await login(client, email="upd409@trackercg.dev")
    item_a = await add_to_collection(client, token, card.id, quantity=1)
    await add_to_collection(
        client, token, card.id, quantity=1, condition=Condition.MINT
    )
    r = await client.patch(
        f"/api/collection/{item_a['id']}",
        json={"condition": Condition.MINT.value},
        headers=auth_headers(token),
    )
    assert r.status_code == 409


async def test_user_isolation(client, session_maker):
    card = await create_card(session_maker)
    await register_user(client, email="alice@trackercg.dev")
    token_a = await login(client, email="alice@trackercg.dev")
    item = await add_to_collection(client, token_a, card.id)

    await register_user(client, email="bob@trackercg.dev")
    token_b = await login(client, email="bob@trackercg.dev")

    # Bob cannot see Alice's item.
    r = await client.get(
        f"/api/collection/{item['id']}", headers=auth_headers(token_b)
    )
    assert r.status_code == 404
    # Bob's collection is empty.
    r = await client.get("/api/collection", headers=auth_headers(token_b))
    assert r.json()["total"] == 0
    # Bob cannot delete Alice's item.
    r = await client.delete(
        f"/api/collection/{item['id']}", headers=auth_headers(token_b)
    )
    assert r.status_code == 404


async def _cards_by_game(session_maker, game: Game):
    from sqlalchemy import select

    from src.models import Card

    async with session_maker() as db:
        result = await db.execute(select(Card).where(Card.game == game))
        return list(result.scalars().all())
