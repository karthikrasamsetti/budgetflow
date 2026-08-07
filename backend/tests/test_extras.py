"""Phase 4 extras tests."""

import pytest_asyncio

REG = {"email": "x4@example.com", "password": "supersecret1", "currency": "INR"}


@pytest_asyncio.fixture
async def auth(client):
    await client.post("/auth/register", json=REG)
    r = await client.post("/auth/login", json={"email": REG["email"], "password": REG["password"]})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def _food_id(client, auth):
    cats = (await client.get("/categories", headers=auth)).json()
    return next(c for c in cats if c["name"] == "Food")["id"]


async def test_goal_lifecycle(client, auth):
    g = await client.post("/goals", json={"name": "Laptop", "target_amount": "80000"}, headers=auth)
    assert g.status_code == 201
    gid = g.json()["id"]

    c = await client.post(f"/goals/{gid}/contribute", json={"amount": "5000"}, headers=auth)
    assert c.json()["saved_amount"] == "5000.00"

    c2 = await client.post(f"/goals/{gid}/contribute", json={"amount": "2500"}, headers=auth)
    assert c2.json()["saved_amount"] == "7500.00"

    assert (await client.delete(f"/goals/{gid}", headers=auth)).status_code == 204
    assert (await client.get("/goals", headers=auth)).json() == []


async def test_csv_export_import_roundtrip(client, auth):
    fid = await _food_id(client, auth)
    for amt in ("100.00", "250.50"):
        await client.post(
            "/transactions",
            json={
                "amount": amt,
                "kind": "expense",
                "occurred_on": "2025-06-10",
                "category_id": fid,
            },
            headers=auth,
        )
    csv_text = (await client.get("/export/csv", headers=auth)).text
    assert "occurred_on,kind,amount" in csv_text
    assert "250.50" in csv_text

    imp = await client.post(
        "/import/csv", content=csv_text, headers={**auth, "Content-Type": "text/csv"}
    )
    assert imp.json()["imported"] == 2  # two data rows re-imported
    # Now 4 total (2 original + 2 imported).
    assert len((await client.get("/transactions", headers=auth)).json()) == 4


async def test_rollover_carries_unspent(client, auth):
    fid = await _food_id(client, auth)
    budget = await client.post(
        "/budgets",
        json={"category_id": fid, "amount": "1000", "rollover_enabled": True},
        headers=auth,
    )
    assert budget.status_code == 201
    # Spend 400 in May -> 600 unspent.
    await client.post(
        "/transactions",
        json={"amount": "400", "kind": "expense", "occurred_on": "2025-05-15", "category_id": fid},
        headers=auth,
    )
    r = await client.post("/budgets/rollover", params={"month": "2025-06"}, headers=auth)
    assert r.json()["rollovers"] == 1
    # Idempotent: second run creates nothing.
    r2 = await client.post("/budgets/rollover", params={"month": "2025-06"}, headers=auth)
    assert r2.json()["rollovers"] == 0


async def test_anomaly_detection(client, auth):
    fid = await _food_id(client, auth)
    # Baseline: 1000/month across Mar, Apr, May (avg 1000).
    for m in ("2025-03", "2025-04", "2025-05"):
        await client.post(
            "/transactions",
            json={
                "amount": "1000",
                "kind": "expense",
                "occurred_on": f"{m}-10",
                "category_id": fid,
            },
            headers=auth,
        )
    # June spike: 3000 (3x avg).
    await client.post(
        "/transactions",
        json={"amount": "3000", "kind": "expense", "occurred_on": "2025-06-10", "category_id": fid},
        headers=auth,
    )
    r = await client.get("/reports/anomalies", params={"month": "2025-06"}, headers=auth)
    anomalies = r.json()["anomalies"]
    assert len(anomalies) == 1
    assert anomalies[0]["category_id"] == fid
    assert anomalies[0]["ratio"] >= 2.0


async def test_ai_usage_empty(client, auth):
    r = await client.get("/ai/usage", headers=auth)
    d = r.json()
    assert d["calls"] == 0 and d["total_tokens"] == 0
