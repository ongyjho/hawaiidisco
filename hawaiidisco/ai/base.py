"""AI Provider protocol definition."""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class AIProvider(Protocol):
    """Interface for AI text generation providers."""

    def generate(self, prompt: str, *, timeout: int = 30) -> str | None:
        """Generate text from a prompt. Return None on failure."""
        ...

    def is_available(self) -> bool:
        """Check whether the provider is available."""
        ...

    @property
    def name(self) -> str:
        """Return the provider name."""
        ...
