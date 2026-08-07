"""Abstract AI provider interface and shared result types."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ChatResult:
    text: str
    usage: Usage = field(default_factory=Usage)


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class ToolCallResult:
    """Either the model called tools, or it returned plain text."""

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    usage: Usage = field(default_factory=Usage)


class AIProvider(ABC):
    """Every provider implements this. Adding one = new subclass + registry entry."""

    name: str
    model: str

    @abstractmethod
    async def chat(self, messages: list[dict]) -> ChatResult:
        """Plain text generation."""

    @abstractmethod
    async def chat_with_tools(self, messages: list[dict], tools: list[dict]) -> ToolCallResult:
        """Function-calling turn. Providers without tool support raise NotImplementedError."""

    @property
    def capabilities(self) -> dict:
        return {"chat": True, "tools": True}
