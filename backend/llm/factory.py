from __future__ import annotations

from .base import LLMProvider, ProviderError
from .claude import ClaudeProvider
from .openai_provider import OpenAIProvider


def create_provider(llm_settings: dict) -> LLMProvider:
    provider = str(llm_settings.get("provider", "claude")).lower().strip()
    keys = llm_settings.get("api_keys", {})
    if provider == "claude":
        return ClaudeProvider(keys.get("claude", ""), llm_settings.get("model", ""))
    if provider == "openai":
        return OpenAIProvider(keys.get("openai", ""), llm_settings.get("openai_model", ""))
    raise ProviderError(f"Unsupported AI provider: {provider}")
