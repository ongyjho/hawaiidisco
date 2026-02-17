"""Bookmark list screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.css.query import NoMatches
from textual.widgets import ListView, ListItem, Static

from hawaiidisco.db import Article
from hawaiidisco.i18n import t
from hawaiidisco.utils import _escape


class BookmarkItem(ListItem):
    """Individual item in the bookmark list."""

    def __init__(
        self,
        article: Article,
        memo: str | None = None,
        tags: list[str] | None = None,
    ) -> None:
        super().__init__()
        self.article = article
        self._memo = memo
        self._tags = tags or []

    def compose(self) -> ComposeResult:
        yield Static(self._format())

    def _format(self) -> str:
        a = self.article
        date_str = ""
        if a.published_at:
            date_str = a.published_at.strftime("%Y-%m-%d")
        elif a.fetched_at:
            date_str = a.fetched_at.strftime("%Y-%m-%d")

        line1 = f"[bold yellow]★[/] [bold]{_escape(a.title)}[/]"
        line2 = f"  [cyan]{_escape(a.feed_name)}[/] · [dim]{date_str}[/]"
        lines = [line1, line2]
        if self._tags:
            lines.append(f"  [dim]🏷 {_escape(', '.join(self._tags))}[/]")
        if a.insight:
            lines.append(f"  [green]{_escape(a.insight)}[/]")
        if self._memo:
            preview = self._memo if len(self._memo) <= 50 else self._memo[:47] + "..."
            lines.append(f"  [italic dim]{_escape(preview)}[/]")
        return "\n".join(lines)


class BookmarkListScreen(ModalScreen[str | None]):
    """Bookmark list screen."""

    BINDINGS = [
        Binding("escape", "dismiss_screen", "Close"),
        Binding("q", "dismiss_screen", "Close"),
    ]

    DEFAULT_CSS = """
    BookmarkListScreen {
        align: center middle;
    }
    #bookmark-list-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: solid $primary;
    }
    #bookmark-list-title {
        text-align: center;
        text-style: bold;
        padding: 1 2;
    }
    #bookmark-analysis {
        max-height: 40%;
        padding: 1 2;
        overflow-y: auto;
        border-bottom: solid $primary;
    }
    #bookmark-articles-title {
        text-style: bold;
        padding: 0 2;
    }
    #bookmark-listview {
        height: 1fr;
    }
    """

    def __init__(
        self,
        articles: list[Article],
        memos: dict[str, str],
        tags: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__()
        self._articles = articles
        self._memos = memos
        self._tags = tags or {}

    def compose(self) -> ComposeResult:
        with Vertical(id="bookmark-list-container"):
            yield Static("Bookmarks", id="bookmark-list-title")
            if not self._articles:
                yield Static(
                    "[dim]No bookmarked articles.[/]",
                    id="bookmark-empty",
                )
            else:
                yield Static(t("bookmark_articles_section"), id="bookmark-articles-title")
                lv = ListView(id="bookmark-listview")
                yield lv

    def on_mount(self) -> None:
        if not self._articles:
            return
        lv = self.query_one("#bookmark-listview", ListView)
        for article in self._articles:
            memo = self._memos.get(article.id)
            article_tags = self._tags.get(article.id, [])
            lv.append(BookmarkItem(article, memo, article_tags))

    def update_analysis(self, text: str) -> None:
        """AI 분석 결과를 갱신한다."""
        try:
            self.query_one("#bookmark-analysis", Static).update(_escape(text))
        except NoMatches:
            pass

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, BookmarkItem):
            self.dismiss(event.item.article.id)

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)

    def key_j(self) -> None:
        try:
            lv = self.query_one("#bookmark-listview", ListView)
            lv.action_cursor_down()
        except NoMatches:
            pass

    def key_k(self) -> None:
        try:
            lv = self.query_one("#bookmark-listview", ListView)
            lv.action_cursor_up()
        except NoMatches:
            pass
