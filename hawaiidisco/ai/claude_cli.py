"""Claude CLI-based AI Provider."""
from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


class ClaudeCLIProvider:
    """Provider that invokes Claude CLI via subprocess."""

    _available: bool | None = None

    def __init__(self, model: str = "") -> None:
        self._model = model or "haiku"

    def generate(self, prompt: str, *, timeout: int = 30, max_tokens: int = 4096) -> str | None:
        """Generate text using the Claude CLI."""
        if not self.is_available():
            return None
        try:
            cmd = ["claude", "-p", prompt, "--model", self._model]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            if result.returncode != 0:
                logger.debug("Claude CLI failed (rc=%d): %s", result.returncode, result.stderr.strip())
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            logger.debug("Claude CLI error", exc_info=True)
        return None

    def is_available(self) -> bool:
        """Check whether the Claude CLI is installed."""
        if ClaudeCLIProvider._available is None:
            ClaudeCLIProvider._available = shutil.which("claude") is not None
        return ClaudeCLIProvider._available

    @property
    def name(self) -> str:
        return "claude_cli"
