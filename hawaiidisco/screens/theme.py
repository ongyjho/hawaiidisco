"""Theme selection screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.css.query import NoMatches
from textual.widgets import ListView, ListItem, Static

from hawaiidisco.i18n import t
from hawaiidisco.utils import _escape


class ThemeItem(ListItem):
    """테마 목록의 개별 항목."""

    def __init__(self, theme_name: str, is_dark: bool, is_current: bool) -> None:
        super().__init__()
        self.theme_name = theme_name
        self._is_dark = is_dark
        self._is_current = is_current

    def compose(self) -> ComposeResult:
        yield Static(self._format())

    def _format(self) -> str:
        marker = "[bold green]● [/]" if self._is_current else "  "
        mode = t("theme_dark") if self._is_dark else t("theme_light")
        return f"{marker}[bold]{_escape(self.theme_name)}[/]  [dim]({mode})[/]"


class ThemeListScreen(ModalScreen[str | None]):
    """테마 선택 모달."""

    BINDINGS = [
        Binding("escape", "dismiss_screen", "Close"),
        Binding("q", "dismiss_screen", "Close"),
    ]

    DEFAULT_CSS = """
    ThemeListScreen {
        align: center middle;
    }
    #theme-list-container {
        width: 50%;
        height: 70%;
        background: $surface;
        border: solid $primary;
    }
    #theme-list-title {
        text-align: center;
        text-style: bold;
        padding: 1 2;
    }
    #theme-listview {
        height: 1fr;
    }
    """

    def __init__(self, themes: list[tuple[str, bool]], current_theme: str) -> None:
        super().__init__()
        self._themes = themes
        self._current_theme = current_theme

    def compose(self) -> ComposeResult:
        with Vertical(id="theme-list-container"):
            yield Static(t("theme_list_title"), id="theme-list-title")
            yield ListView(id="theme-listview")

    def on_mount(self) -> None:
        lv = self.query_one("#theme-listview", ListView)
        for name, is_dark in self._themes:
            lv.append(ThemeItem(name, is_dark, name == self._current_theme))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, ThemeItem):
            self.dismiss(event.item.theme_name)

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)

    def key_j(self) -> None:
        try:
            self.query_one("#theme-listview", ListView).action_cursor_down()
        except NoMatches:
            pass

    def key_k(self) -> None:
        try:
            self.query_one("#theme-listview", ListView).action_cursor_up()
        except NoMatches:
            pass
