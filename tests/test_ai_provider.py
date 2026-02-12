"""Tests for AI Provider Protocol compliance and behavior."""
from __future__ import annotations

from unittest.mock import MagicMock

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.ai.claude_cli import ClaudeCLIProvider
from hawaiidisco.ai import get_provider
from hawaiidisco.config import AIConfig


class TestAIProviderProtocol:
    """Verify AIProvider Protocol implementation."""

    def test_claude_cli_implements_protocol(self) -> None:
        """ClaudeCLIProvider implements the AIProvider Protocol."""
        provider = ClaudeCLIProvider()
        assert isinstance(provider, AIProvider)

    def test_mock_provider_implements_protocol(self) -> None:
        """Mock provider implements the AIProvider Protocol."""
        mock = MagicMock(spec=AIProvider)
        mock.name = "mock"
        assert isinstance(mock, AIProvider)

    def test_claude_cli_provider_name(self) -> None:
        """ClaudeCLIProvider's name is 'claude_cli'."""
        provider = ClaudeCLIProvider()
        assert provider.name == "claude_cli"


class TestGetProvider:
    """Tests for the get_provider factory function."""

    def test_default_returns_claude_cli(self) -> None:
        """Default returns ClaudeCLIProvider."""
        config = AIConfig()
        provider = get_provider(config)
        assert isinstance(provider, ClaudeCLIProvider)

    def test_claude_cli_explicit(self) -> None:
        """Return ClaudeCLIProvider when provider='claude_cli'."""
        config = AIConfig(provider="claude_cli")
        provider = get_provider(config)
        assert isinstance(provider, ClaudeCLIProvider)


class TestClaudeCLIProvider:
    """Tests for ClaudeCLIProvider behavior."""

    def test_generate_returns_none_when_unavailable(self) -> None:
        """Return None when Claude CLI is not available."""
        provider = ClaudeCLIProvider()
        # force cache to False
        original = ClaudeCLIProvider._available
        ClaudeCLIProvider._available = False
        try:
            result = provider.generate("test prompt")
            assert result is None
        finally:
            ClaudeCLIProvider._available = original

    def test_is_available_returns_bool(self) -> None:
        """is_available returns a bool."""
        provider = ClaudeCLIProvider()
        # reset cache for actual check
        original = ClaudeCLIProvider._available
        ClaudeCLIProvider._available = None
        try:
            result = provider.is_available()
            assert isinstance(result, bool)
        finally:
            ClaudeCLIProvider._available = original
