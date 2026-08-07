"""AI provider factory + logging wrapper tests. No network calls."""

import pytest

from budgetflow.ai.base import ChatResult, Usage
from budgetflow.ai.factory import (
    ProviderNotAvailable,
    available_providers,
    get_provider,
)
from budgetflow.ai.logging import logged_call
from budgetflow.config import Settings, get_settings


@pytest.fixture(autouse=True)
def _reset_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_available_lists_all_registered(monkeypatch):
    providers = available_providers()
    names = {p["name"] for p in providers}
    assert names == {"groq", "gemini", "hf"}
    # Exactly one default.
    assert sum(p["is_default"] for p in providers) == 1


def test_configured_flag_reflects_api_key(monkeypatch):
    monkeypatch.setattr(
        "budgetflow.ai.factory.get_settings",
        lambda: Settings(groq_api_key="k", gemini_api_key=None, hf_api_key=None),
    )
    by_name = {p["name"]: p for p in available_providers()}
    assert by_name["groq"]["configured"] is True
    assert by_name["gemini"]["configured"] is False


def test_get_provider_unknown_raises(monkeypatch):
    monkeypatch.setattr("budgetflow.ai.factory.get_settings", lambda: Settings())
    with pytest.raises(ProviderNotAvailable):
        get_provider("does-not-exist")


def test_get_provider_missing_key_raises(monkeypatch):
    monkeypatch.setattr(
        "budgetflow.ai.factory.get_settings",
        lambda: Settings(groq_api_key=None),
    )
    with pytest.raises(ProviderNotAvailable):
        get_provider("groq")


def test_get_provider_builds_when_configured(monkeypatch):
    monkeypatch.setattr(
        "budgetflow.ai.factory.get_settings",
        lambda: Settings(groq_api_key="k", default_ai_provider="groq"),
    )
    provider = get_provider()  # default
    assert provider.name == "groq"


async def test_logged_call_writes_ok_row(session_factory):
    async with session_factory() as db:

        async def fake():
            return ChatResult(text="hi", usage=Usage(3, 4, 7))

        result = await logged_call(
            db, provider="groq", model="m", intent="chat", call=fake, user_id=None
        )
        assert result.text == "hi"

        from budgetflow.models import AILog

        rows = (await db.execute(__import__("sqlalchemy").select(AILog))).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "ok"
        assert rows[0].total_tokens == 7


async def test_logged_call_records_error_and_reraises(session_factory):
    async with session_factory() as db:

        async def boom():
            raise RuntimeError("provider exploded")

        with pytest.raises(RuntimeError):
            await logged_call(db, provider="hf", model="m", intent="qa", call=boom)

        from sqlalchemy import select

        from budgetflow.models import AILog

        rows = (await db.execute(select(AILog))).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "error"
        assert "exploded" in rows[0].error
