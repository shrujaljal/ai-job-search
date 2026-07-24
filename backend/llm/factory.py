from __future__ import annotations

from .base import LLMProvider, ProviderError
from .claude import ClaudeProvider
from .openai_compatible import OpenAICompatibleProvider
from .openai_provider import OpenAIProvider


def create_provider(llm_settings: dict) -> LLMProvider:
    provider = str(llm_settings.get("provider", "claude")).lower().strip()
    keys = llm_settings.get("api_keys", {})
    if provider == "claude":
        return ClaudeProvider(keys.get("claude", ""), llm_settings.get("model", ""))
    if provider == "openai":
        return OpenAIProvider(keys.get("openai", ""), llm_settings.get("openai_model", ""))
    if provider == "openrouter":
        return OpenAICompatibleProvider(
            name="openrouter",
            api_key=keys.get("openrouter", ""),
            model=llm_settings.get("openrouter_model", "") or "openrouter/free",
            base_url="https://openrouter.ai/api/v1",
        )
    if provider == "groq":
        return OpenAICompatibleProvider(
            name="groq",
            api_key=keys.get("groq", ""),
            model=llm_settings.get("groq_model", "") or "openai/gpt-oss-20b",
            base_url="https://api.groq.com/openai/v1",
        )
    if provider == "ollama":
        return OpenAICompatibleProvider(
            name="ollama",
            api_key="ollama",
            model=llm_settings.get("ollama_model", "") or "gpt-oss:20b",
            base_url=llm_settings.get("ollama_base_url", "") or "http://localhost:11434/v1",
            key_required=False,
        )
    raise ProviderError(f"Unsupported AI provider: {provider}")
