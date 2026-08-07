"""ChatService orchestrates the assistant: persist turns, route intent, act.

Every provider call flows through logged_call (one ai_logs row). Sessions and
messages give multi-turn memory. NL-add tries provider structured output first,
then the regex parser as a deterministic fallback.
"""

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..ai.categorizer import categorize
from ..ai.factory import ProviderNotAvailable, get_provider
from ..ai.logging import logged_call
from ..ai.parsers import has_relative_date, parse_nl_add, resolve_relative_date
from ..ai.router import NL_ADD, QA, route
from ..ai.tools import TOOL_SCHEMAS, dispatch
from ..models import ChatSession, Message


def _nl_add_system(today: date) -> str:
    return (
        f"Today's date is {today.isoformat()}. Resolve relative dates like 'today' "
        f"and 'yesterday' against it. Extract a transaction from the user message. "
        'Respond ONLY with JSON: {"amount": number, "kind": "income"|"expense", '
        '"occurred_on": "YYYY-MM-DD", "category": string|null, "note": string}. '
        "No prose, no markdown."
    )


class ChatService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # --- session persistence ---
    async def _get_or_create_session(
        self, user_id: int, session_id: int | None, first_message: str
    ) -> ChatSession:
        if session_id is not None:
            s = await self.db.get(ChatSession, session_id)
            if s and s.user_id == user_id and not s.is_deleted:
                return s
        s = ChatSession(user_id=user_id, title=first_message[:60])
        self.db.add(s)
        await self.db.commit()
        await self.db.refresh(s)
        return s

    async def _history(self, session_id: int) -> list[dict]:
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at, Message.id)
        )
        return [{"role": m.role, "content": m.content} for m in result.scalars().all()]

    async def _add_message(self, session_id: int, role: str, content: str) -> None:
        self.db.add(Message(session_id=session_id, role=role, content=content))
        await self.db.commit()

    async def list_sessions(self, user_id: int) -> list[ChatSession]:
        result = await self.db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id, ChatSession.is_deleted.is_(False))
            .order_by(ChatSession.updated_at.desc())
        )
        return list(result.scalars().all())

    async def get_messages(self, user_id: int, session_id: int) -> list[Message]:
        s = await self.db.get(ChatSession, session_id)
        if not s or s.user_id != user_id or s.is_deleted:
            return []
        result = await self.db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at, Message.id)
        )
        return list(result.scalars().all())

    # --- main entry ---
    async def handle(
        self, user_id: int, message: str, *, session_id: int | None, provider: str | None
    ) -> dict:
        session = await self._get_or_create_session(user_id, session_id, message)
        await self._add_message(session.id, "user", message)

        intent = route(message)
        try:
            if intent == NL_ADD:
                reply, action = await self._do_nl_add(user_id, message, provider, session.id)
            elif intent == QA:
                reply, action = await self._do_qa(user_id, message, provider, session.id)
            else:
                reply, action = await self._do_text(user_id, message, provider, session.id, intent)
        except ProviderNotAvailable:
            reply, action = (
                "No AI provider is configured. Set an API key to enable the assistant.",
                None,
            )

        await self._add_message(session.id, "assistant", reply)
        return {"session_id": session.id, "intent": intent, "reply": reply, "action": action}

    # --- intent handlers ---
    async def _do_nl_add(self, user_id, message, provider, session_id):
        from ..services.transaction_service import TransactionService

        today = date.today()
        parsed = await self._structured_nl_add(user_id, message, provider, session_id, today)
        if parsed is None:
            parsed = parse_nl_add(message, today=today)
        if parsed is None:
            return "I couldn't find an amount to record. Try 'spent 500 on food'.", None

        cat_id = await categorize(
            self.db,
            user_id,
            parsed.get("category_hint") or parsed.get("category"),
            parsed["kind"],
        )

        # Resolve the date ourselves. If the message says today/yesterday, that
        # wins over whatever the model returned (models hallucinate stale dates).
        if has_relative_date(message):
            occurred = resolve_relative_date(message, today)
        else:
            occurred = parsed["occurred_on"]
            if isinstance(occurred, str):
                try:
                    occurred = date.fromisoformat(occurred)
                except ValueError:
                    occurred = today
            # Guard against implausible dates from the model.
            if not isinstance(occurred, date) or occurred.year < 2000 or occurred > today:
                occurred = today

        tx = await TransactionService(self.db).create(
            user_id,
            amount=parsed["amount"],
            kind=parsed["kind"],
            occurred_on=occurred,
            category_id=cat_id,
            note=parsed.get("note"),
            source="ai",
        )
        reply = f"Recorded {parsed['kind']} of {parsed['amount']} on {occurred.isoformat()}."
        return reply, {"type": "transaction_created", "transaction_id": tx.id}

    async def _structured_nl_add(
        self, user_id, message, provider, session_id, today
    ) -> dict | None:
        """Try provider structured output. Returns parsed dict or None on any failure."""
        try:
            prov = get_provider(provider)
        except ProviderNotAvailable:
            return None
        messages = [
            {"role": "system", "content": _nl_add_system(today)},
            {"role": "user", "content": message},
        ]
        try:
            result = await logged_call(
                self.db,
                provider=prov.name,
                model=prov.model,
                intent="nl_add",
                user_id=user_id,
                session_id=session_id,
                call=lambda: prov.chat(messages),
            )
            data = json.loads(result.text.strip().strip("`").removeprefix("json").strip())
            if "amount" not in data:
                return None
            from decimal import Decimal

            return {
                "amount": Decimal(str(data["amount"])),
                "kind": data.get("kind", "expense"),
                "occurred_on": data.get("occurred_on") or today.isoformat(),
                "category": data.get("category"),
                "note": data.get("note") or message,
            }
        except Exception:  # noqa: BLE001 - any failure => use regex fallback
            return None

    async def _do_qa(self, user_id, message, provider, session_id):
        prov = get_provider(provider)
        history = await self._history(session_id)
        messages = [
            {
                "role": "system",
                "content": "You answer questions about the user's finances. Use tools to "
                "fetch real numbers before answering. Be concise.",
            },
            *history,
        ]
        result = await logged_call(
            self.db,
            provider=prov.name,
            model=prov.model,
            intent="qa",
            user_id=user_id,
            session_id=session_id,
            call=lambda: prov.chat_with_tools(messages, TOOL_SCHEMAS),
        )
        if not result.tool_calls:
            return (result.text or "I don't have enough data to answer that."), None

        tool_results = []
        for tc in result.tool_calls:
            out = await dispatch(self.db, user_id, tc.name, tc.arguments)
            tool_results.append({"tool": tc.name, "result": out})

        # Second turn: give tool results back to the model for a natural answer.
        follow = messages + [
            {"role": "assistant", "content": f"tool_results={json.dumps(tool_results)}"},
            {"role": "user", "content": "Answer using those results, concisely."},
        ]
        final = await logged_call(
            self.db,
            provider=prov.name,
            model=prov.model,
            intent="qa",
            user_id=user_id,
            session_id=session_id,
            call=lambda: prov.chat(follow),
        )
        return final.text, {"type": "tool_calls", "results": tool_results}

    async def _do_text(self, user_id, message, provider, session_id, intent):
        prov = get_provider(provider)
        history = await self._history(session_id)
        system = (
            "You are a helpful budgeting assistant. Give a brief monthly overview or advice."
            if intent == "insights"
            else "You are a helpful budgeting assistant. Be concise and friendly."
        )
        messages = [{"role": "system", "content": system}, *history]
        result = await logged_call(
            self.db,
            provider=prov.name,
            model=prov.model,
            intent=intent,
            user_id=user_id,
            session_id=session_id,
            call=lambda: prov.chat(messages),
        )
        return result.text, None