"""Bookmark memo input screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static, TextArea

from hawaiidisco.i18n import t


class MemoScreen(ModalScreen[str]):
    """Bookmark memo input screen."""

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    DEFAULT_CSS = """
    MemoScreen {
        align: center middle;
    }
    #memo-container {
        width: 60;
        height: 12;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }
    #memo-title {
        text-align: center;
        padding-bottom: 1;
    }
    #memo-input {
        height: 6;
    }
    """

    def __init__(self, current_memo: str = "") -> None:
        super().__init__()
        self._current_memo = current_memo

    def compose(self) -> ComposeResult:
        with Vertical(id="memo-container"):
            yield Static(t("memo_input_help"), id="memo-title")
            yield TextArea(self._current_memo, id="memo-input")

    def key_ctrl_s(self) -> None:
        text_area = self.query_one("#memo-input", TextArea)
        self.dismiss(text_area.text)

    def action_cancel(self) -> None:
        self.dismiss("")
