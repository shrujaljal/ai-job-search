from __future__ import annotations

from .base import LLMProvider, ProviderError


class OpenAICompatibleProvider(LLMProvider):
    """Provider adapter for APIs that implement OpenAI chat completions."""

    def __init__(
        self,
        *,
        name: str,
        api_key: str,
        model: str,
        base_url: str | None = None,
        key_required: bool = True,
    ) -> None:
        if key_required and not api_key.strip():
            raise ProviderError(f"{name} API key is not configured.")
        self.name = name
        self.model = model.strip()
        self._api_key = api_key.strip() or "local"
        self._base_url = base_url
        if not self.model:
            raise ProviderError(f"{name} model is not configured.")

    def complete_json(self, system_prompt: str, user_prompt: str) -> str:
        try:
            from openai import OpenAI

            client_args = {
                "api_key": self._api_key,
                "timeout": 60.0,
                "max_retries": 1,
            }
            if self._base_url:
                client_args["base_url"] = self._base_url
            response = OpenAI(**client_args).chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            text = response.choices[0].message.content or ""
        except Exception as exc:
            raise ProviderError(f"{self.name} request failed: {exc}") from exc
        if not text.strip():
            raise ProviderError(f"{self.name} returned an empty response.")
        return text
