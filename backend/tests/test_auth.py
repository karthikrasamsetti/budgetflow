"""Auth flow tests against an in-memory DB."""

import pytest

REG = {"email": "user@example.com", "password": "supersecret1", "currency": "INR"}


async def test_register_then_login_and_me(client):
    r = await client.post("/auth/register", json=REG)
    assert r.status_code == 201, r.text
    assert r.json()["email"] == REG["email"]

    r = await client.post("/auth/login", json={"email": REG["email"], "password": REG["password"]})
    assert r.status_code == 200, r.text
    tokens = r.json()
    assert tokens["access_token"] and tokens["refresh_token"]

    r = await client.get("/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    assert r.json()["email"] == REG["email"]


async def test_duplicate_email_rejected(client):
    await client.post("/auth/register", json=REG)
    r = await client.post("/auth/register", json=REG)
    assert r.status_code == 409


async def test_login_wrong_password(client):
    await client.post("/auth/register", json=REG)
    r = await client.post("/auth/login", json={"email": REG["email"], "password": "wrongpass1"})
    assert r.status_code == 401


async def test_me_requires_auth(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_refresh_issues_new_tokens(client):
    await client.post("/auth/register", json=REG)
    login = await client.post(
        "/auth/login", json={"email": REG["email"], "password": REG["password"]}
    )
    refresh = login.json()["refresh_token"]
    r = await client.post("/auth/refresh", json={"refresh_token": refresh})
    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_access_token_rejected_as_refresh(client):
    await client.post("/auth/register", json=REG)
    login = await client.post(
        "/auth/login", json={"email": REG["email"], "password": REG["password"]}
    )
    access = login.json()["access_token"]
    r = await client.post("/auth/refresh", json={"refresh_token": access})
    assert r.status_code == 401


async def test_password_reset_flow(client):
    await client.post("/auth/register", json=REG)
    req = await client.post("/auth/password-reset/request", json={"email": REG["email"]})
    assert req.status_code == 200
    token = req.json()["debug_reset_token"]  # dev-only convenience

    confirm = await client.post(
        "/auth/password-reset/confirm",
        json={"token": token, "new_password": "brandnewpass9"},
    )
    assert confirm.status_code == 200

    # Old password no longer works; new one does.
    old = await client.post(
        "/auth/login", json={"email": REG["email"], "password": REG["password"]}
    )
    assert old.status_code == 401
    new = await client.post(
        "/auth/login", json={"email": REG["email"], "password": "brandnewpass9"}
    )
    assert new.status_code == 200


async def test_reset_request_unknown_email_still_200(client):
    r = await client.post("/auth/password-reset/request", json={"email": "nobody@example.com"})
    assert r.status_code == 200
    assert "debug_reset_token" not in r.json()


@pytest.mark.parametrize("bad", [{"email": "x", "password": "y"}, {"password": "short"}])
async def test_register_validation(client, bad):
    r = await client.post("/auth/register", json=bad)
    assert r.status_code == 422
