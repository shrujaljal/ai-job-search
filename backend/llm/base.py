from __future__ import annotations

from abc import ABC, abstractmethod


class ProviderError(RuntimeError):
    """A provider request failed or returned unusable content."""


class LLMProvider(ABC):
    name: str
    model: str

    @abstractmethod
    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        """Return the provider's raw JSON response text."""
