"""Tag management screens."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.css.query import NoMatches
from textual.widgets import Input, ListView, ListItem, Static

from hawaiidisco.i18n import t
from hawaiidisco.utils import _escape


class TagEditScreen(ModalScreen[str]):
    """태그 편집 모달."""

    DEFAULT_CSS = """
    TagEditScreen {
        align: center middle;
    }
    #tag-container {
        width: 55;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }
    """

    def __init__(self, current_tags: str = "") -> None:
        super().__init__()
        self._current_tags = current_tags

    def compose(self) -> ComposeResult:
        with Vertical(id="tag-container"):
            yield Static(t("tag_edit_help"))
            yield Input(
                value=self._current_tags,
                placeholder=t("tag_placeholder"),
                id="tag-input",
            )

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)

    def key_escape(self) -> None:
        self.dismiss("")


class TagItem(ListItem):
    """태그 목록의 개별 항목."""

    def __init__(self, tag: str, count: int) -> None:
        super().__init__()
        self.tag = tag
        self._count = count

    def compose(self) -> ComposeResult:
        yield Static(self._format())

    def _format(self) -> str:
        return (
            f"[bold cyan]{_escape(self.tag)}[/]"
            f"  [dim]{t('tag_count', count=self._count)}[/]"
        )


class TagListScreen(ModalScreen[str | None]):
    """태그 필터 목록 모달."""

    BINDINGS = [
        Binding("escape", "dismiss_screen", "Close"),
        Binding("q", "dismiss_screen", "Close"),
    ]

    DEFAULT_CSS = """
    TagListScreen {
        align: center middle;
    }
    #tag-list-container {
        width: 60%;
        height: 70%;
        background: $surface;
        border: solid $primary;
    }
    #tag-list-title {
        text-align: center;
        text-style: bold;
        padding: 1 2;
    }
    #tag-listview {
        height: 1fr;
    }
    """

    def __init__(self, tags_with_counts: list[tuple[str, int]]) -> None:
        super().__init__()
        self._tags = tags_with_counts

    def compose(self) -> ComposeResult:
        with Vertical(id="tag-list-container"):
            yield Static(t("tag_list_title"), id="tag-list-title")
            if not self._tags:
                yield Static(f"[dim]{t('no_tags')}[/]", id="tag-empty")
            else:
                yield ListView(id="tag-listview")

    def on_mount(self) -> None:
        if not self._tags:
            return
        lv = self.query_one("#tag-listview", ListView)
        for tag, count in self._tags:
            lv.append(TagItem(tag, count))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, TagItem):
            self.dismiss(event.item.tag)

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)

    def key_j(self) -> None:
        try:
            self.query_one("#tag-listview", ListView).action_cursor_down()
        except NoMatches:
            pass

    def key_k(self) -> None:
        try:
            self.query_one("#tag-listview", ListView).action_cursor_up()
        except NoMatches:
            pass
