"""OpenAI API-based AI Provider."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class OpenAIProvider:
    """Provider using the OpenAI SDK."""

    def __init__(self, api_key: str = "", model: str = "") -> None:
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self._model = model or "gpt-4o"
        self._client = None

    def _get_client(self):
        """Lazily initialize and return the API client."""
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=self._api_key)
        return self._client

    def generate(self, prompt: str, *, timeout: int = 30) -> str | None:
        """Generate text using the OpenAI API."""
        if not self.is_available():
            return None
        try:
            client = self._get_client()
            response = client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                timeout=timeout,
            )
            if response.choices:
                return response.choices[0].message.content.strip()
        except Exception:
            logger.debug("OpenAI API call failed", exc_info=True)
        return None

    def is_available(self) -> bool:
        """Check whether the API key is configured."""
        return bool(self._api_key)

    @property
    def name(self) -> str:
        return "openai"
