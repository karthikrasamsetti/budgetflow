"""Phase 1 tests: categories, transactions, budgets, recurring."""

import pytest_asyncio

REG = {"email": "u@example.com", "password": "supersecret1", "currency": "INR"}


@pytest_asyncio.fixture
async def auth(client):
    """Register + login, return an Authorization header dict."""
    await client.post("/auth/register", json=REG)
    r = await client.post("/auth/login", json={"email": REG["email"], "password": REG["password"]})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def test_category_create_and_isolation(client, auth):
    r = await client.post("/categories", json={"name": "Coffee", "kind": "expense"}, headers=auth)
    assert r.status_code == 201
    cat_id = r.json()["id"]

    # System categories appear in the list alongside the new one.
    listed = await client.get("/categories", headers=auth)
    names = {c["name"] for c in listed.json()}
    assert "Coffee" in names and "Food" in names  # Food is a seeded system category

    # Cannot edit a system category.
    sys_cat = next(c for c in listed.json() if c["is_system"])
    bad = await client.patch(f"/categories/{sys_cat['id']}", json={"name": "Hax"}, headers=auth)
    assert bad.status_code == 404

    ok = await client.patch(f"/categories/{cat_id}", json={"name": "Espresso"}, headers=auth)
    assert ok.status_code == 200 and ok.json()["name"] == "Espresso"


async def test_transaction_crud_and_soft_delete(client, auth):
    body = {"amount": "500.00", "kind": "expense", "occurred_on": "2025-06-15"}
    created = await client.post("/transactions", json=body, headers=auth)
    assert created.status_code == 201
    tx_id = created.json()["id"]

    got = await client.get(f"/transactions/{tx_id}", headers=auth)
    assert got.status_code == 200 and got.json()["amount"] == "500.00"

    upd = await client.patch(f"/transactions/{tx_id}", json={"amount": "650.00"}, headers=auth)
    assert upd.json()["amount"] == "650.00"

    deleted = await client.delete(f"/transactions/{tx_id}", headers=auth)
    assert deleted.status_code == 204

    # Soft-deleted: gone from reads.
    assert (await client.get(f"/transactions/{tx_id}", headers=auth)).status_code == 404
    listed = await client.get("/transactions", headers=auth)
    assert listed.json() == []


async def test_budget_status_alerts(client, auth):
    cats = (await client.get("/categories", headers=auth)).json()
    food = next(c for c in cats if c["name"] == "Food")

    budget = await client.post(
        "/budgets",
        json={"category_id": food["id"], "amount": "1000.00"},
        headers=auth,
    )
    bid = budget.json()["id"]

    # Spend 850 in June -> crosses the 0.8 threshold but not 1.0.
    await client.post(
        "/transactions",
        json={
            "amount": "850.00",
            "kind": "expense",
            "occurred_on": "2025-06-10",
            "category_id": food["id"],
        },
        headers=auth,
    )
    status = await client.get(f"/budgets/{bid}/status", params={"month": "2025-06"}, headers=auth)
    data = status.json()
    assert data["spent"] == "850.00"
    assert data["remaining"] == "150.00"
    assert data["alerts"] == [0.8]

    # Spend 200 more -> now over 100%.
    await client.post(
        "/transactions",
        json={
            "amount": "200.00",
            "kind": "expense",
            "occurred_on": "2025-06-11",
            "category_id": food["id"],
        },
        headers=auth,
    )
    status2 = await client.get(f"/budgets/{bid}/status", params={"month": "2025-06"}, headers=auth)
    assert status2.json()["alerts"] == [0.8, 1.0]


async def test_recurring_materialize_catches_up(client, auth):
    # A weekly rule starting well in the past should backfill multiple tx.
    rule = await client.post(
        "/recurring",
        json={
            "amount": "100.00",
            "kind": "expense",
            "cadence": "weekly",
            "next_run_on": "2025-06-01",
        },
        headers=auth,
    )
    assert rule.status_code == 201

    run = await client.post("/recurring/run", headers=auth)
    assert run.status_code == 200
    # At least several weeks have passed since 2025-06-01.
    assert run.json()["created"] >= 4

    # All materialized transactions carry source=recurring.
    txs = (await client.get("/transactions", headers=auth)).json()
    assert txs and all(t["source"] == "recurring" for t in txs)

    # Running again immediately creates nothing new (next_run_on advanced).
    again = await client.post("/recurring/run", headers=auth)
    assert again.json()["created"] == 0


async def test_recurring_validation(client, auth):
    bad = await client.post(
        "/recurring",
        json={
            "amount": "100.00",
            "kind": "expense",
            "cadence": "yearly",
            "next_run_on": "2025-06-01",
        },
        headers=auth,
    )
    assert bad.status_code == 400
