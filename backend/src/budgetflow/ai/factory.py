"""AI provider factory. get_provider(name) builds a configured provider.

Adding a provider = register a builder here. No caller changes.
"""

from collections.abc import Callable

from ..config import Settings, get_settings
from .base import AIProvider
from .providers.gemini import GeminiProvider
from .providers.groq import GroqProvider
from .providers.hf import HFProvider


def _build_groq(s: Settings) -> AIProvider | None:
    if not s.groq_api_key:
        return None
    return GroqProvider(api_key=s.groq_api_key, model=s.groq_model)


def _build_gemini(s: Settings) -> AIProvider | None:
    if not s.gemini_api_key:
        return None
    return GeminiProvider(api_key=s.gemini_api_key, model=s.gemini_model)


def _build_hf(s: Settings) -> AIProvider | None:
    if not s.hf_api_key:
        return None
    return HFProvider(api_key=s.hf_api_key, model=s.hf_model)


# name -> builder. Order here is display order in /ai/providers.
_REGISTRY: dict[str, Callable[[Settings], AIProvider | None]] = {
    "groq": _build_groq,
    "gemini": _build_gemini,
    "hf": _build_hf,
}


class ProviderNotAvailable(Exception):
    """Requested provider is unknown or missing an API key."""


def available_providers() -> list[dict]:
    """List every registered provider with whether it's configured, plus the default."""
    s = get_settings()
    out = []
    for name, builder in _REGISTRY.items():
        configured = builder(s) is not None
        out.append(
            {
                "name": name,
                "configured": configured,
                "is_default": name == s.default_ai_provider,
            }
        )
    return out


def get_provider(name: str | None = None) -> AIProvider:
    """Return a ready provider. Falls back to the configured default when name is None."""
    s = get_settings()
    chosen = name or s.default_ai_provider
    builder = _REGISTRY.get(chosen)
    if builder is None:
        raise ProviderNotAvailable(f"Unknown provider: {chosen}")
    provider = builder(s)
    if provider is None:
        raise ProviderNotAvailable(f"Provider '{chosen}' is missing its API key")
    return provider
