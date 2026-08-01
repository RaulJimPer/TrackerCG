"""Security hardening: response headers on all responses."""
from __future__ import annotations


async def test_security_headers_on_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    csp = r.headers.get("content-security-policy", "")
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "object-src 'none'" in csp
    assert r.headers.get("x-frame-options") == "DENY"
    assert r.headers.get("x-content-type-options") == "nosniff"
    assert r.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


async def test_security_headers_on_api(client):
    # Unauthenticated requests also carry the headers (no data leak).
    r = await client.get("/api/collection")
    assert r.status_code == 401
    assert r.headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in r.headers


async def test_login_returns_204_and_cookie(client):
    from test.conftest import TEST_PASSWORD, register_user

    await register_user(client, email="hdr@trackercg.dev")
    r = await client.post(
        "/auth/login",
        data={"username": "hdr@trackercg.dev", "password": TEST_PASSWORD},
    )
    assert r.status_code == 204
    cookie = r.headers.get("set-cookie", "")
    assert "trackercg_session=" in cookie
    assert "HttpOnly" in cookie
    assert "SameSite=strict" in cookie
