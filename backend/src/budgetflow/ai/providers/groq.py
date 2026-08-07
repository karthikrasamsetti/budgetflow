"""Groq provider. OpenAI-compatible /chat/completions endpoint."""

import httpx

from ..base import AIProvider, ChatResult, ToolCall, ToolCallResult, Usage

_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider(AIProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self.model = model

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _usage(self, data: dict) -> Usage:
        u = data.get("usage", {}) or {}
        return Usage(
            prompt_tokens=u.get("prompt_tokens", 0),
            completion_tokens=u.get("completion_tokens", 0),
            total_tokens=u.get("total_tokens", 0),
        )

    async def chat(self, messages: list[dict]) -> ChatResult:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _BASE_URL,
                headers=self._headers(),
                json={"model": self.model, "messages": messages},
            )
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        return ChatResult(text=text, usage=self._usage(data))

    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> ToolCallResult:
        import json

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                _BASE_URL,
                headers=self._headers(),
                json={
                    "model": self.model,
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        msg = data["choices"][0]["message"]
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments") or "{}"
            calls.append(ToolCall(name=fn.get("name", ""), arguments=json.loads(args)))
        return ToolCallResult(text=msg.get("content"), tool_calls=calls, usage=self._usage(data))
