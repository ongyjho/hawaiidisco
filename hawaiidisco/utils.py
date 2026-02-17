"""Shared utility functions."""
from __future__ import annotations


def _escape(text: str) -> str:
    """Escape Rich markup characters in user-supplied text."""
    return text.replace("[", "\\[")
