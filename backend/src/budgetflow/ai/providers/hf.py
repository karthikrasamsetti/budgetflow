"""HuggingFace provider via the router's OpenAI-compatible chat completions endpoint."""

import httpx

from ..base import AIProvider, ChatResult, ToolCallResult, Usage

_BASE_URL = "https://router.huggingface.co/v1/chat/completions"


class HFProvider(AIProvider):
    name = "hf"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self.model = model

    def _usage(self, data: dict) -> Usage:
        u = data.get("usage", {}) or {}
        return Usage(
            prompt_tokens=u.get("prompt_tokens", 0),
            completion_tokens=u.get("completion_tokens", 0),
            total_tokens=u.get("total_tokens", 0),
        )

    async def chat(self, messages: list[dict]) -> ChatResult:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                _BASE_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"model": self.model, "messages": messages},
            )
            resp.raise_for_status()
            data = resp.json()
        text = data["choices"][0]["message"]["content"] or ""
        return ChatResult(text=text, usage=self._usage(data))

    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> ToolCallResult:
        # Tool support varies by HF model; Phase 2 handles the reliable subset.
        result = await self.chat(messages)
        return ToolCallResult(text=result.text, tool_calls=[], usage=result.usage)
