"""Claude CLI-based AI Provider."""
from __future__ import annotations

import shutil
import subprocess


class ClaudeCLIProvider:
    """Provider that invokes Claude CLI via subprocess."""

    _available: bool | None = None

    def generate(self, prompt: str, *, timeout: int = 30, max_tokens: int = 4096) -> str | None:
        """Generate text using the Claude CLI."""
        if not self.is_available():
            return None
        try:
            cmd = ["claude", "-p", prompt, "--max-tokens", str(max_tokens)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def is_available(self) -> bool:
        """Check whether the Claude CLI is installed."""
        if ClaudeCLIProvider._available is None:
            ClaudeCLIProvider._available = shutil.which("claude") is not None
        return ClaudeCLIProvider._available

    @property
    def name(self) -> str:
        return "claude_cli"
