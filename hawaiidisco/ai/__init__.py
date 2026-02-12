"""AI Provider factory."""
from __future__ import annotations

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.ai.claude_cli import ClaudeCLIProvider


def get_provider(ai_config) -> AIProvider:
    """Return the appropriate AI provider based on configuration."""
    name = ai_config.provider

    if name == "anthropic":
        try:
            from hawaiidisco.ai.anthropic_api import AnthropicProvider
            return AnthropicProvider(
                api_key=ai_config.api_key,
                model=ai_config.model,
            )
        except ImportError:
            raise ImportError(
                "anthropic package is required. Install with: pip install hawaiidisco[anthropic]"
            )

    if name == "openai":
        try:
            from hawaiidisco.ai.openai_api import OpenAIProvider
            return OpenAIProvider(
                api_key=ai_config.api_key,
                model=ai_config.model,
            )
        except ImportError:
            raise ImportError(
                "openai package is required. Install with: pip install hawaiidisco[openai]"
            )

    # Default: claude_cli
    return ClaudeCLIProvider()
