from __future__ import annotations

from .base import LLMProvider, ProviderError


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key.strip():
            raise ProviderError("OpenAI API key is not configured.")
        self.model = model.strip() or "gpt-4o"
        self._api_key = api_key

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import OpenAI

            response = OpenAI(api_key=self._api_key, timeout=45.0, max_retries=1).chat.completions.create(
                model=self.model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = response.choices[0].message.content or ""
        except Exception as exc:
            raise ProviderError(f"OpenAI request failed: {exc}") from exc
        if not text.strip():
            raise ProviderError("OpenAI returned an empty response.")
        return text
