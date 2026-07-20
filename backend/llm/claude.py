from __future__ import annotations

from .base import LLMProvider, ProviderError


class ClaudeProvider(LLMProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key.strip():
            raise ProviderError("Anthropic API key is not configured.")
        self.model = model.strip() or "claude-sonnet-5"
        self._api_key = api_key

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from anthropic import Anthropic

            response = Anthropic(api_key=self._api_key, timeout=45.0, max_retries=1).messages.create(
                model=self.model,
                max_tokens=3000,
                temperature=0,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = "".join(
                block.text for block in response.content
                if getattr(block, "type", "") == "text"
            )
        except Exception as exc:
            raise ProviderError(f"Anthropic request failed: {exc}") from exc
        if not text.strip():
            raise ProviderError("Anthropic returned an empty response.")
        return text
