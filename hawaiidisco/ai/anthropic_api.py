"""Anthropic API-based AI Provider."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class AnthropicProvider:
    """Provider using the Anthropic SDK."""

    def __init__(self, api_key: str = "", model: str = "") -> None:
        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self._model = model or "claude-sonnet-4-5-20250929"
        self._client = None

    def _get_client(self):
        """Lazily initialize and return the API client."""
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    def generate(self, prompt: str, *, timeout: int = 30, max_tokens: int = 4096) -> str | None:
        """Generate text using the Anthropic API."""
        if not self.is_available():
            return None
        try:
            client = self._get_client()
            message = client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout,
            )
            if message.content:
                return message.content[0].text.strip()
        except Exception:
            logger.debug("Anthropic API 호출 실패", exc_info=True)
        return None

    def is_available(self) -> bool:
        """Check whether the API key is configured."""
        return bool(self._api_key)

    @property
    def name(self) -> str:
        return "anthropic"
