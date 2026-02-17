"""OPML import screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Static

from hawaiidisco.i18n import t


class OpmlImportScreen(ModalScreen[str]):
    """OPML file path input screen."""

    DEFAULT_CSS = """
    OpmlImportScreen {
        align: center middle;
    }
    #opml-container {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="opml-container"):
            yield Static(t("opml_import_help"))
            yield Input(placeholder=t("opml_path_placeholder"), id="opml-path")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip())

    def key_escape(self) -> None:
        self.dismiss("")
