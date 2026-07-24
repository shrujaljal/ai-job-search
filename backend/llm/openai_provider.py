from __future__ import annotations

from .openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    def __init__(self, api_key: str, model: str) -> None:
        super().__init__(
            name="openai",
            api_key=api_key,
            model=model.strip() or "gpt-4o",
        )
