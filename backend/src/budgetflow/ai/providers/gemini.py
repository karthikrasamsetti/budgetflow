"""Gemini provider. Google Generative Language REST API.

Note: Gemini model names retire periodically. If a call 404s on the model,
resolve the current name via the ListModels endpoint and update gemini_model.
"""

import httpx

from ..base import AIProvider, ChatResult, ToolCall, ToolCallResult, Usage

_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _to_gemini_contents(messages: list[dict]) -> list[dict]:
    """Map OpenAI-style roles to Gemini 'contents'. System folds into first user turn."""
    contents = []
    system_prefix = ""
    for m in messages:
        role = m["role"]
        if role == "system":
            system_prefix += m["content"] + "\n\n"
            continue
        text = m["content"]
        if role == "user" and system_prefix:
            text = system_prefix + text
            system_prefix = ""
        contents.append(
            {"role": "model" if role == "assistant" else "user", "parts": [{"text": text}]}
        )
    return contents


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self.model = model

    def _usage(self, data: dict) -> Usage:
        u = data.get("usageMetadata", {}) or {}
        return Usage(
            prompt_tokens=u.get("promptTokenCount", 0),
            completion_tokens=u.get("candidatesTokenCount", 0),
            total_tokens=u.get("totalTokenCount", 0),
        )

    async def chat(self, messages: list[dict]) -> ChatResult:
        url = f"{_BASE}/{self.model}:generateContent?key={self._api_key}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json={"contents": _to_gemini_contents(messages)})
            resp.raise_for_status()
            data = resp.json()
        try:
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            text = ""
        return ChatResult(text=text, usage=self._usage(data))

    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> ToolCallResult:
        # Gemini function-calling uses a different tool schema. For Phase 0 the
        # factory exposes Gemini; tool-calling wiring lands in Phase 2. Fall back
        # to plain chat so the provider is usable now.
        result = await self.chat(messages)
        return ToolCallResult(text=result.text, tool_calls=[], usage=result.usage)


# Keep ToolCall import referenced for future tool wiring.
__all__ = ["GeminiProvider", "ToolCall"]
