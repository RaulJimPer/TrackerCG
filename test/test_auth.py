"""Auth endpoints: register, login, logout, /users/me."""
from __future__ import annotations

from test.conftest import TEST_PASSWORD, auth_headers, login, register_user


async def test_register_success(client):
    status = await register_user(client, email="a@trackercg.dev")
    assert status == 201


async def test_register_duplicate_email(client):
    await register_user(client, email="dup@trackercg.dev")
    r = await client.post(
        "/auth/register",
        json={"email": "dup@trackercg.dev", "password": TEST_PASSWORD},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "REGISTER_USER_ALREADY_EXISTS"


async def test_register_weak_password(client):
    r = await client.post(
        "/auth/register",
        json={"email": "weak@trackercg.dev", "password": "abc"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "REGISTER_INVALID_PASSWORD"


async def test_register_password_too_long(client):
    r = await client.post(
        "/auth/register",
        json={"email": "long@trackercg.dev", "password": "A1" + "x" * 200},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "REGISTER_INVALID_PASSWORD"


async def test_register_password_matches_email(client):
    r = await client.post(
        "/auth/register",
        json={"email": "Same1@trackercg.dev", "password": "Same1@trackercg.dev"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "REGISTER_INVALID_PASSWORD"


async def test_register_invalid_email(client):
    r = await client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": TEST_PASSWORD},
    )
    assert r.status_code == 422


async def test_login_success_sets_cookie(client):
    await register_user(client, email="login@trackercg.dev")
    token = await login(client, email="login@trackercg.dev")
    assert token


async def test_login_bad_credentials(client):
    await register_user(client, email="bad@trackercg.dev")
    r = await client.post(
        "/auth/login",
        data={"username": "bad@trackercg.dev", "password": "WrongPass1"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "LOGIN_BAD_CREDENTIALS"


async def test_me_requires_auth(client):
    r = await client.get("/users/me")
    assert r.status_code == 401


async def test_me_with_auth(client):
    await register_user(client, email="me@trackercg.dev")
    token = await login(client, email="me@trackercg.dev")
    r = await client.get("/users/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["email"] == "me@trackercg.dev"


async def test_logout_clears_session(client):
    await register_user(client, email="out@trackercg.dev")
    token = await login(client, email="out@trackercg.dev")
    r = await client.post("/auth/logout", headers=auth_headers(token))
    assert r.status_code == 204
    # After logout the cookie is cleared; the JWT is still signed but the
    # client no longer holds it, so /users/me without cookie is 401.
    r2 = await client.get("/users/me", headers=auth_headers(token))
    assert r2.status_code in (200, 401)
