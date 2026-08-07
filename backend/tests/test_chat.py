"""Phase 2 tests: intent router, NL parser, and chat flows with a mock provider."""

import json
from datetime import date

import pytest_asyncio

from budgetflow.ai import router as intent_router
from budgetflow.ai.base import ChatResult, ToolCall, ToolCallResult, Usage
from budgetflow.ai.parsers import parse_nl_add

REG = {"email": "c@example.com", "password": "supersecret1", "currency": "INR"}


# --- pure unit tests (no DB) ---
def test_router_classifies():
    assert intent_router.route("spent 500 on food") == intent_router.NL_ADD
    assert intent_router.route("how much did I spend on food?") == intent_router.QA
    assert intent_router.route("give me a summary this month") == intent_router.INSIGHTS
    assert intent_router.route("hello there") == intent_router.CHAT


def test_parser_extracts():
    p = parse_nl_add("spent 500 on food yesterday", today=date(2025, 6, 10))
    assert p["amount"] == 500 and p["kind"] == "expense"
    assert p["occurred_on"] == date(2025, 6, 9)
    assert p["category_hint"] == "Food"

    inc = parse_nl_add("received 20000 salary")
    assert inc["kind"] == "income"

    assert parse_nl_add("no numbers here") is None


# --- chat flow tests (mock provider injected) ---
@pytest_asyncio.fixture
async def auth(client):
    await client.post("/auth/register", json=REG)
    r = await client.post("/auth/login", json={"email": REG["email"], "password": REG["password"]})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


class MockProvider:
    """Deterministic provider: no network. Behavior varies by system prompt."""

    name = "mock"
    model = "mock-1"

    async def chat(self, messages):
        sys = messages[0]["content"] if messages else ""
        if "Respond ONLY with JSON" in sys:  # NL-add structured path
            payload = {
                "amount": 450,
                "kind": "expense",
                "occurred_on": "2025-06-15",
                "category": "Food",
                "note": "pizza",
            }
            return ChatResult(text=json.dumps(payload), usage=Usage(10, 5, 15))
        return ChatResult(text="Here is a concise answer.", usage=Usage(8, 4, 12))

    async def chat_with_tools(self, messages, tools):
        return ToolCallResult(
            tool_calls=[ToolCall(name="get_spending_by_category", arguments={"category": "Food"})],
            usage=Usage(6, 3, 9),
        )


@pytest_asyncio.fixture(autouse=True)
def _mock_provider(monkeypatch):
    monkeypatch.setattr(
        "budgetflow.services.chat_service.get_provider", lambda name=None: MockProvider()
    )


async def test_chat_nl_add_creates_transaction(client, auth):
    r = await client.post("/chat", json={"message": "spent 450 on pizza"}, headers=auth)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["intent"] == "nl_add"
    assert data["action"]["type"] == "transaction_created"

    # The transaction is real and readable via the core API.
    txs = (await client.get("/transactions", headers=auth)).json()
    assert len(txs) == 1 and txs[0]["source"] == "ai"


async def test_chat_nl_add_uses_today_not_model_date(client, auth):
    # MockProvider returns a stale 2025-06-15 date; a 'today' message must override it.
    from datetime import date

    r = await client.post(
        "/chat", json={"message": "add expense 500 in transport today"}, headers=auth
    )
    assert r.status_code == 200
    txs = (await client.get("/transactions", headers=auth)).json()
    assert txs[0]["occurred_on"] == date.today().isoformat()


async def test_chat_qa_uses_tools(client, auth):
    # Seed a Food expense so the tool has something to report.
    cats = (await client.get("/categories", headers=auth)).json()
    food = next(c for c in cats if c["name"] == "Food")
    await client.post(
        "/transactions",
        json={
            "amount": "300.00",
            "kind": "expense",
            "occurred_on": date.today().isoformat(),
            "category_id": food["id"],
        },
        headers=auth,
    )
    r = await client.post("/chat", json={"message": "how much did I spend on food?"}, headers=auth)
    data = r.json()
    assert data["intent"] == "qa"
    assert data["action"]["type"] == "tool_calls"
    assert data["action"]["results"][0]["result"]["spent"] == "300.00"


async def test_chat_persists_session_and_multi_turn(client, auth):
    r1 = await client.post("/chat", json={"message": "hello"}, headers=auth)
    sid = r1.json()["session_id"]
    r2 = await client.post("/chat", json={"message": "and again", "session_id": sid}, headers=auth)
    assert r2.json()["session_id"] == sid

    sessions = (await client.get("/chat/sessions", headers=auth)).json()
    assert len(sessions) == 1

    msgs = (await client.get(f"/chat/sessions/{sid}", headers=auth)).json()
    # 2 user + 2 assistant turns.
    assert len(msgs) == 4
    assert [m["role"] for m in msgs] == ["user", "assistant", "user", "assistant"]


async def test_chat_logs_ai_calls(client, auth, session_factory):
    await client.post("/chat", json={"message": "give me a summary"}, headers=auth)
    from sqlalchemy import select

    from budgetflow.models import AILog

    async with session_factory() as db:
        rows = (await db.execute(select(AILog))).scalars().all()
    assert len(rows) >= 1
    assert all(r.status == "ok" for r in rows)