"""Digest display screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.css.query import NoMatches
from textual.widgets import Static

from hawaiidisco.i18n import t


class DigestScreen(ModalScreen[None]):
    """Weekly digest display modal with vim-style scrolling."""

    BINDINGS = [
        Binding("escape", "dismiss_screen", "Close"),
        Binding("q", "dismiss_screen", "Close"),
        Binding("S", "save_to_obsidian", t("save_to_obsidian")),
        Binding("N", "save_to_notion", t("save_to_notion")),
    ]

    DEFAULT_CSS = """
    DigestScreen {
        align: center middle;
    }
    #digest-container {
        width: 85%;
        height: 85%;
        background: $surface;
        border: solid $primary;
    }
    #digest-title {
        text-align: center;
        text-style: bold;
        padding: 1 2;
        color: $accent;
    }
    #digest-scroll {
        height: 1fr;
    }
    #digest-body {
        padding: 1 2;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._content: str = ""
        self._article_count: int = 0

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="digest-container"):
            yield Static(t("digest_title"), id="digest-title")
            yield Static(t("generating_digest"), id="digest-body")

    def update_content(self, content: str, article_count: int) -> None:
        """Update the digest content after background generation."""
        self._content = content
        self._article_count = article_count
        try:
            body = self.query_one("#digest-body", Static)
            body.update(content + f"\n\n[dim]{t('digest_article_count', count=article_count)}[/]")
        except NoMatches:
            pass

    def update_error(self, message: str) -> None:
        """Show an error message in the digest body."""
        try:
            body = self.query_one("#digest-body", Static)
            body.update(f"[red]{message}[/]")
        except NoMatches:
            pass

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)

    def action_save_to_obsidian(self) -> None:
        """Trigger Obsidian save via the app."""
        if self._content:
            self.app._save_digest_to_obsidian(self._content, self._article_count)  # type: ignore[attr-defined]

    def action_save_to_notion(self) -> None:
        """Trigger Notion save via the app."""
        if self._content:
            self.app._save_digest_to_notion(self._content, self._article_count)  # type: ignore[attr-defined]

    # Vim-style scrolling
    def key_j(self) -> None:
        try:
            self.query_one("#digest-container", VerticalScroll).scroll_down()
        except NoMatches:
            pass

    def key_k(self) -> None:
        try:
            self.query_one("#digest-container", VerticalScroll).scroll_up()
        except NoMatches:
            pass

    def key_g(self) -> None:
        try:
            self.query_one("#digest-container", VerticalScroll).scroll_home()
        except NoMatches:
            pass

    def key_G(self) -> None:  # noqa: N802
        try:
            self.query_one("#digest-container", VerticalScroll).scroll_end()
        except NoMatches:
            pass
