"""Rate limiting (slowapi) — 429 responses after exceeding limits."""
from __future__ import annotations

from test.conftest import auth_headers, login, register_user

SEARCH_LIMIT = 30  # matches the @limiter.limit("30/minute") on /api/cards/search


async def test_search_rate_limit_429(client):
    await register_user(client, email="rl@trackercg.dev")
    token = await login(client, email="rl@trackercg.dev")
    headers = auth_headers(token)

    statuses = []
    for _ in range(SEARCH_LIMIT + 2):
        r = await client.get("/api/cards/search", params={"q": "zzz"}, headers=headers)
        statuses.append(r.status_code)

    assert statuses.count(429) >= 1
    # The final responses must carry the slowapi rate-limit headers; the
    # custom 429 handler reports the configured limit as the exact amount.
    assert "x-ratelimit-limit" in r.headers
    assert r.headers.get("x-ratelimit-limit") == str(SEARCH_LIMIT)


async def test_headers_enabled(client):
    await register_user(client, email="rl2@trackercg.dev")
    token = await login(client, email="rl2@trackercg.dev")
    r = await client.get("/api/cards/search", params={"q": "zzz"}, headers=auth_headers(token))
    assert "x-ratelimit-limit" in r.headers
    assert "x-ratelimit-remaining" in r.headers
