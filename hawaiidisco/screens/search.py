"""Search input screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from hawaiidisco.i18n import t


class SearchScreen(ModalScreen[str]):
    """Search input screen."""

    DEFAULT_CSS = """
    SearchScreen {
        align: center middle;
    }
    #search-container {
        width: 50;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="search-container"):
            yield Static(t("search_help"))
            yield Input(placeholder=t("search_placeholder"), id="search-input")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def key_escape(self) -> None:
        self.dismiss("")
