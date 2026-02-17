"""Textual main application."""
from __future__ import annotations

import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path


from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.css.query import NoMatches
from textual.widgets import Input, ListView, ListItem, Static, TabbedContent, TabPane, TextArea

from hawaiidisco.ai import get_provider
from hawaiidisco.config import Config, FeedConfig, load_config, ensure_dirs, add_feed, remove_feed
from hawaiidisco.opml import parse_opml, export_opml
from hawaiidisco.i18n import t
from hawaiidisco.reader import fetch_article_text
from hawaiidisco.db import Article, Database
from hawaiidisco.fetcher import fetch_all_feeds
from hawaiidisco.insight import get_or_generate_insight
from hawaiidisco.bookmark import save_bookmark_md, delete_bookmark_md
from hawaiidisco.obsidian import save_obsidian_note, delete_obsidian_note, validate_vault_path
from hawaiidisco.translate import translate_article_meta, translate_text
from hawaiidisco.widgets.timeline import Timeline
from hawaiidisco.widgets.detail import DetailView
from hawaiidisco.widgets.status import StatusBar


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


class ArticleScreen(ModalScreen):
    """Article body viewer screen."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("q", "dismiss", "Close"),
        Binding("o", "open_browser", "Browser"),
        Binding("t", "translate_body", "Translate"),
        Binding("i", "insight", "Insight"),
        Binding("j", "scroll_down", "Down", show=False),
        Binding("k", "scroll_up", "Up", show=False),
        Binding("down", "scroll_down", "Down", show=False),
        Binding("up", "scroll_up", "Up", show=False),
        Binding("pagedown", "page_down", "Page Down", show=False),
        Binding("pageup", "page_up", "Page Up", show=False),
        Binding("g", "scroll_home", "Top", show=False),
        Binding("G", "scroll_end", "Bottom", show=False),
    ]

    DEFAULT_CSS = """
    ArticleScreen {
        align: center middle;
    }
    #article-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: solid $primary;
    }
    #article-header {
        padding: 1 2;
        height: auto;
        max-height: 5;
        background: $primary-background;
    }
    .article-scroll {
        height: 1fr;
        padding: 1 2;
    }
    """

    def __init__(
        self,
        title: str,
        meta: str,
        body: str,
        link: str,
        article_id: str | None = None,
        translated_body: str | None = None,
        description: str | None = None,
        insight: str | None = None,
    ) -> None:
        super().__init__()
        self._title = title
        self._meta = meta
        self._body = body
        self._link = link
        self._article_id = article_id
        self._translated_body = translated_body
        self._description = description
        self._insight = insight

    def compose(self) -> ComposeResult:
        with Vertical(id="article-container"):
            yield Static(
                f"[bold]{_escape(self._title)}[/]\n[dim]{_escape(self._meta)}[/]",
                id="article-header",
            )
            with TabbedContent(id="article-tabs"):
                with TabPane(t("original"), id="tab-original"):
                    with VerticalScroll(classes="article-scroll"):
                        yield Static(
                            _escape(self._body) or f"[dim]{t('loading_body')}[/]",
                            id="article-body",
                        )
                with TabPane(t("translation_tab"), id="tab-translated"):
                    with VerticalScroll(classes="article-scroll"):
                        yield Static(
                            _escape(self._translated_body) if self._translated_body
                            else f"[dim]{t('press_t_to_translate')}[/]",
                            id="translated-body",
                        )
                with TabPane(t("insight_tab"), id="tab-insight"):
                    with VerticalScroll(classes="article-scroll"):
                        yield Static(
                            _escape(self._insight) if self._insight
                            else f"[dim]{t('press_i_for_insight')}[/]",
                            id="insight-body",
                        )

    def on_mount(self) -> None:
        # Activate insight tab if cached insight exists
        if self._insight:
            try:
                self.query_one("#article-tabs", TabbedContent).active = "tab-insight"
            except NoMatches:
                pass
        # Activate translation tab if cached translation exists (lower priority than insight)
        elif self._translated_body:
            try:
                self.query_one("#article-tabs", TabbedContent).active = "tab-translated"
            except NoMatches:
                pass

    def _get_active_scroll(self) -> VerticalScroll | None:
        """현재 활성 탭의 VerticalScroll 위젯을 반환한다."""
        try:
            tabs = self.query_one("#article-tabs", TabbedContent)
            pane = tabs.get_pane(tabs.active)
            return pane.query_one(VerticalScroll)
        except (NoMatches, Exception):
            return None

    def action_scroll_down(self) -> None:
        if sw := self._get_active_scroll():
            sw.scroll_down(animate=False)

    def action_scroll_up(self) -> None:
        if sw := self._get_active_scroll():
            sw.scroll_up(animate=False)

    def action_page_down(self) -> None:
        if sw := self._get_active_scroll():
            sw.scroll_page_down(animate=False)

    def action_page_up(self) -> None:
        if sw := self._get_active_scroll():
            sw.scroll_page_up(animate=False)

    def action_scroll_home(self) -> None:
        if sw := self._get_active_scroll():
            sw.scroll_home(animate=False)

    def action_scroll_end(self) -> None:
        if sw := self._get_active_scroll():
            sw.scroll_end(animate=False)

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    def action_open_browser(self) -> None:
        if not self._link.startswith(("http://", "https://")):
            return
        import webbrowser as wb
        wb.open(self._link)

    def update_body(self, text: str) -> None:
        """Update the original tab body text."""
        self._body = text
        try:
            self.query_one("#article-body", Static).update(_escape(text))
        except NoMatches:
            pass  # Not mounted yet; self._body will be used in compose

    def update_translated_body(self, text: str) -> None:
        """Update the translation tab body and activate the translation tab."""
        self._translated_body = text
        try:
            self.query_one("#translated-body", Static).update(_escape(text))
            self.query_one("#article-tabs", TabbedContent).active = "tab-translated"
        except NoMatches:
            pass  # Not mounted yet; self._translated_body will be used in compose

    def action_translate_body(self) -> None:
        """Toggle translation tab. Request translation if none exists."""
        try:
            tabs = self.query_one("#article-tabs", TabbedContent)
        except NoMatches:
            return

        if self._translated_body:
            # Toggle tab if translation already exists
            if tabs.active == "tab-translated":
                tabs.active = "tab-original"
            else:
                tabs.active = "tab-translated"
            return

        # Request translation if none exists
        self.query_one("#translated-body", Static).update(f"[dim]{t('translating')}[/]")
        tabs.active = "tab-translated"
        self.app._translate_article_body(self)  # type: ignore[attr-defined]

    def update_insight(self, text: str) -> None:
        """Update the insight tab body and activate the insight tab."""
        self._insight = text
        try:
            self.query_one("#insight-body", Static).update(_escape(text))
            self.query_one("#article-tabs", TabbedContent).active = "tab-insight"
        except NoMatches:
            pass  # Not mounted yet; self._insight will be used in compose

    def action_insight(self) -> None:
        """Toggle insight tab. Request generation if none exists."""
        try:
            tabs = self.query_one("#article-tabs", TabbedContent)
        except NoMatches:
            return

        if self._insight:
            # Toggle tab if insight already exists
            if tabs.active == "tab-insight":
                tabs.active = "tab-original"
            else:
                tabs.active = "tab-insight"
            return

        # Request generation if no insight exists
        self.query_one("#insight-body", Static).update(
            f"[dim]{t('generating_insight')}[/]"
        )
        tabs.active = "tab-insight"
        self.app._generate_insight_for_screen(self)  # type: ignore[attr-defined]


def _escape(text: str) -> str:
    """Escape Rich markup characters."""
    return text.replace("[", "\\[")


class AddFeedScreen(ModalScreen[tuple]):
    """Feed addition input screen."""

    DEFAULT_CSS = """
    AddFeedScreen {
        align: center middle;
    }
    #add-feed-container {
        width: 65;
        height: 10;
        padding: 1 2;
        background: $surface;
        border: solid $primary;
    }
    #add-feed-title {
        text-align: center;
        padding-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="add-feed-container"):
            yield Static(t("add_feed_help"), id="add-feed-title")
            yield Input(placeholder=t("rss_url_placeholder"), id="feed-url")
            yield Input(placeholder=t("feed_name_placeholder"), id="feed-name")

    def on_mount(self) -> None:
        self.query_one("#feed-url", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "feed-url":
            self.query_one("#feed-name", Input).focus()
        elif event.input.id == "feed-name":
            url = self.query_one("#feed-url", Input).value.strip()
            name = self.query_one("#feed-name", Input).value.strip()
            # http(s) 스키마만 허용
            if url and url.startswith(("http://", "https://")):
                self.dismiss((url, name or url))
            elif url:
                self.query_one("#feed-url", Input).value = ""
                self.query_one("#feed-url", Input).placeholder = t("invalid_url_scheme")
                self.query_one("#feed-url", Input).focus()
            else:
                self.dismiss(())

    def key_escape(self) -> None:
        self.dismiss(())


class ConfirmDeleteScreen(ModalScreen[bool]):
    """삭제 확인 모달."""

    DEFAULT_CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    #confirm-container {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: solid $error;
    }
    #confirm-message {
        text-align: center;
        padding-bottom: 1;
    }
    #confirm-hint {
        text-align: center;
        color: $text-muted;
    }
    """

    def __init__(self, message: str) -> None:
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(id="confirm-container"):
            yield Static(self._message, id="confirm-message")
            yield Static(t("confirm_delete_hint"), id="confirm-hint")

    def key_y(self) -> None:
        self.dismiss(True)

    def key_n(self) -> None:
        self.dismiss(False)

    def key_escape(self) -> None:
        self.dismiss(False)


class FeedItem(ListItem):
    """Individual item in the feed list."""

    def __init__(self, feed: FeedConfig, count: int) -> None:
        super().__init__()
        self.feed = feed
        self._count = count

    def compose(self) -> ComposeResult:
        yield Static(self._format())

    def _format(self) -> str:
        return (
            f"[bold cyan]{_escape(self.feed.name)}[/]\n"
            f"  [dim]{_escape(self.feed.url)}[/]\n"
            f"  {t('article_count', count=self._count)}"
        )


class FeedListScreen(ModalScreen[str | None]):
    """Subscribed feed list screen."""

    BINDINGS = [
        Binding("escape", "dismiss_screen", "Close"),
        Binding("q", "dismiss_screen", "Close"),
    ]

    DEFAULT_CSS = """
    FeedListScreen {
        align: center middle;
    }
    #feed-list-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: solid $primary;
    }
    #feed-list-title {
        text-align: center;
        text-style: bold;
        padding: 1 2;
    }
    #feed-listview {
        height: 1fr;
    }
    """

    def __init__(
        self,
        feeds: list[FeedConfig],
        counts: dict[str, int],
    ) -> None:
        super().__init__()
        self._feeds = feeds
        self._counts = counts

    def compose(self) -> ComposeResult:
        with Vertical(id="feed-list-container"):
            yield Static(t("feed_list_title"), id="feed-list-title")
            if not self._feeds:
                yield Static(
                    f"[dim]{t('no_feeds')}[/]",
                    id="feed-empty",
                )
            else:
                yield ListView(id="feed-listview")

    def on_mount(self) -> None:
        if not self._feeds:
            return
        lv = self.query_one("#feed-listview", ListView)
        for feed in self._feeds:
            count = self._counts.get(feed.name, 0)
            lv.append(FeedItem(feed, count))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, FeedItem):
            self.dismiss(event.item.feed.name)

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)

    def key_j(self) -> None:
        try:
            self.query_one("#feed-listview", ListView).action_cursor_down()
        except NoMatches:
            pass

    def key_k(self) -> None:
        try:
            self.query_one("#feed-listview", ListView).action_cursor_up()
        except NoMatches:
            pass

    def key_d(self) -> None:
        """선택된 피드 삭제 확인 모달을 띄운다."""
        try:
            lv = self.query_one("#feed-listview", ListView)
        except NoMatches:
            return
        if lv.highlighted_child is None or not isinstance(lv.highlighted_child, FeedItem):
            return
        feed_item: FeedItem = lv.highlighted_child
        feed = feed_item.feed
        count = feed_item._count
        msg = t("confirm_delete_feed", name=feed.name, count=count)
        self.app.push_screen(
            ConfirmDeleteScreen(msg),
            lambda confirmed: self._do_delete(confirmed, feed),
        )

    def _do_delete(self, confirmed: bool, feed: FeedConfig) -> None:
        """삭제 확인 후 실제 삭제를 수행한다."""
        if not confirmed:
            return
        self.app._do_delete_feed(feed)  # type: ignore[attr-defined]
        self.dismiss(None)


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


class HawaiiDiscoApp(App):
    """Hawaii Disco - Terminal RSS Reader."""

    TITLE = "Hawaii Disco"
    CSS = """
    Timeline {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("b", "bookmark", "Bookmark"),
        Binding("m", "memo", "Memo"),
        Binding("enter", "read_article", "Read", show=False),
        Binding("space", "read_article", "Read", show=False),
        Binding("o", "open_browser", "Browser"),
        Binding("l", "bookmark_list", "Bookmarks"),
        Binding("slash", "search", "Search"),
        Binding("escape", "clear_search", "Clear search", show=False),
        Binding("f", "filter_bookmarks", "Filter"),
        Binding("a", "add_feed", "Add feed"),
        Binding("L", "feed_list", "Feeds"),
        Binding("t", "translate", "Translate"),
        Binding("c", "edit_tags", "Tags"),
        Binding("T", "tag_list", "Tag list"),
        Binding("S", "save_obsidian", t("save_to_obsidian")),
        Binding("V", "select_theme", "Theme"),
        Binding("I", "import_opml", "Import OPML"),
        Binding("E", "export_opml", "Export OPML"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config: Config = load_config()
        ensure_dirs(self.config)
        self.db = Database(self.config.db_path)
        self.ai = get_provider(self.config.ai)
        self._current_article: Article | None = None
        self._bookmark_filter: bool = False
        self._search_query: str | None = None
        self._feed_filter: str | None = None
        self._tag_filter: str | None = None
        self.theme = self.config.theme

        # Validate Obsidian vault path at startup
        if self.config.obsidian.enabled and not validate_vault_path(self.config.obsidian):
            import sys

            print(
                f"Warning: Obsidian vault path not found: {self.config.obsidian.vault_path}",
                file=sys.stderr,
            )

    def compose(self) -> ComposeResult:
        yield Timeline([], id="timeline")
        yield DetailView()
        yield StatusBar()

    def on_mount(self) -> None:
        self._do_refresh()

    # --- Event Handlers ---

    def on_timeline_article_highlighted(self, event: Timeline.ArticleHighlighted) -> None:
        self._current_article = event.article
        try:
            self.query_one(DetailView).show_article(event.article)
        except NoMatches:
            pass

    def on_timeline_article_selected(self, event: Timeline.ArticleSelected) -> None:
        self._read_article(event.article)

    # --- Actions ---

    def action_refresh(self) -> None:
        self._do_refresh()

    @work(thread=True)
    def _do_refresh(self) -> None:
        """Fetch feeds in the background."""
        try:
            status = self.query_one(StatusBar)
        except NoMatches:
            return
        self.call_from_thread(status.set_message, t("refreshing"))

        new_count = fetch_all_feeds(self.config.feeds, self.db, allow_insecure_ssl=self.config.allow_insecure_ssl)
        now = datetime.now()

        if new_count > 0:
            msg = t("new_articles_found", count=new_count)
            self._notify_macos(msg)
        else:
            msg = t("no_new_articles")

        self.call_from_thread(status.set_message, msg)
        self.call_from_thread(status.set_last_refresh, now)
        self.call_from_thread(self._reload_articles)

        # Clear message after a short delay
        import time
        time.sleep(3)
        self.call_from_thread(status.set_message, "")

    def _reload_articles(self) -> None:
        """Reload the article list according to current filter settings."""
        if self._tag_filter:
            articles = self.db.get_articles_by_tag(self._tag_filter)
        else:
            articles = self.db.get_articles(
                bookmarked_only=self._bookmark_filter,
                search=self._search_query,
                feed_name=self._feed_filter,
            )
        # 태그 정보를 일괄 조회하여 Timeline에 전달
        all_tags = self.db.get_all_bookmark_tags()
        try:
            timeline = self.query_one(Timeline)
        except NoMatches:
            return
        timeline.refresh_articles(articles, all_tags)

    def action_read_article(self) -> None:
        article = self._get_current_article()
        if article:
            self._read_article(article)

    def _read_article(self, article: Article) -> None:
        """Display the article body in the TUI."""
        self.db.mark_read(article.id)
        self._reload_articles()

        meta = f"{article.feed_name}"
        if article.published_at:
            meta += f" · {article.published_at.strftime('%Y-%m-%d %H:%M')}"
        meta += f"\n{article.link}"

        # Open screen with description first, then fetch full text in background
        screen = ArticleScreen(
            title=article.title,
            meta=meta,
            body=article.description or t("loading_body"),
            link=article.link,
            article_id=article.id,
            translated_body=article.translated_body,
            description=article.description,
            insight=article.insight,
        )
        self.push_screen(screen)
        self._fetch_full_article(article.link, screen)

    @work(thread=True)
    def _fetch_full_article(self, url: str, screen: ArticleScreen) -> None:
        text = fetch_article_text(url, allow_insecure_ssl=self.config.allow_insecure_ssl)
        self.call_from_thread(screen.update_body, text)

    def action_open_browser(self) -> None:
        article = self._get_current_article()
        if article and article.link.startswith(("http://", "https://")):
            self.db.mark_read(article.id)
            webbrowser.open(article.link)
            self._reload_articles()

    @work(thread=True)
    def _generate_insight_for_screen(self, screen: ArticleScreen) -> None:
        """Generate insight for an ArticleScreen. Check DB cache first, generate if missing."""
        article_id = screen._article_id

        if not self.ai.is_available():
            self.call_from_thread(screen.update_insight, t("claude_cli_not_found"))
            return

        # Check DB cache
        if article_id:
            cached = self.db.get_article(article_id)
            if cached and cached.insight:
                self.call_from_thread(screen.update_insight, cached.insight)
                return

        # Build Article object from description and generate insight
        if article_id:
            article = self.db.get_article(article_id)
        else:
            article = None

        if article:
            insight = get_or_generate_insight(article, self.db, self.ai)
            self.call_from_thread(screen.update_insight, insight)
            self.call_from_thread(self._reload_articles)

            # Refresh detail view on main screen
            updated = self.db.get_article(article_id)
            if updated:
                try:
                    detail = self.query_one(DetailView)
                    self.call_from_thread(detail.show_article, updated)
                except NoMatches:
                    pass
        else:
            self.call_from_thread(screen.update_insight, t("insight_failed"))

    def action_bookmark(self) -> None:
        article = self._get_current_article()
        if not article:
            return
        new_state = self.db.toggle_bookmark(article.id)
        status = self.query_one(StatusBar)

        if new_state:
            updated = self.db.get_article(article.id)
            if updated:
                save_bookmark_md(updated, self.config.bookmark_dir)
                # Auto-save to Obsidian if enabled
                if self.config.obsidian.enabled and self.config.obsidian.auto_save:
                    if validate_vault_path(self.config.obsidian):
                        try:
                            tags = self.db.get_bookmark_tags(article.id)
                            save_obsidian_note(updated, self.config.obsidian, tags=tags)
                            status.set_message(t("obsidian_auto_saved", title=article.title[:30]))
                            self._reload_articles()
                            return
                        except Exception:
                            pass  # Fall through to standard bookmark message
            status.set_message(t("bookmark_added", title=article.title[:30]))
        else:
            delete_bookmark_md(article, self.config.bookmark_dir)
            if self.config.obsidian.enabled and self.config.obsidian.auto_save:
                if validate_vault_path(self.config.obsidian):
                    try:
                        delete_obsidian_note(article, self.config.obsidian)
                    except Exception:
                        pass
            status.set_message(t("bookmark_removed", title=article.title[:30]))

        self._reload_articles()

    def action_memo(self) -> None:
        article = self._get_current_article()
        if not article or not article.is_bookmarked:
            self.query_one(StatusBar).set_message(t("bookmark_first"))
            return

        current_memo = self.db.get_bookmark_memo(article.id) or ""
        self.push_screen(MemoScreen(current_memo), self._on_memo_result)

    def _on_memo_result(self, memo: str) -> None:
        article = self._get_current_article()
        if not article or not memo:
            return
        self.db.set_bookmark_memo(article.id, memo)
        updated = self.db.get_article(article.id)
        if updated:
            save_bookmark_md(updated, self.config.bookmark_dir, memo)
            # Update Obsidian note too
            if self.config.obsidian.enabled and self.config.obsidian.auto_save:
                if validate_vault_path(self.config.obsidian):
                    try:
                        tags = self.db.get_bookmark_tags(article.id)
                        save_obsidian_note(updated, self.config.obsidian, memo=memo, tags=tags)
                    except Exception:
                        pass
        self.query_one(StatusBar).set_message(t("memo_saved"))

    def action_save_obsidian(self) -> None:
        """Manually save the current article to Obsidian vault."""
        article = self._get_current_article()
        if not article:
            return
        if not self.config.obsidian.enabled:
            self.query_one(StatusBar).set_message(t("obsidian_not_configured"))
            return
        if not validate_vault_path(self.config.obsidian):
            self.query_one(StatusBar).set_message(
                t("obsidian_vault_not_found", path=str(self.config.obsidian.vault_path))
            )
            return

        updated = self.db.get_article(article.id)
        if not updated:
            return

        memo = self.db.get_bookmark_memo(article.id)
        tags = self.db.get_bookmark_tags(article.id)

        try:
            save_obsidian_note(updated, self.config.obsidian, memo=memo, tags=tags)
            self.query_one(StatusBar).set_message(
                t("obsidian_saved", title=article.title[:30])
            )
        except Exception as exc:
            self.query_one(StatusBar).set_message(
                t("obsidian_save_failed", error=type(exc).__name__)
            )

    def action_search(self) -> None:
        self.push_screen(SearchScreen(), self._on_search_result)

    def _on_search_result(self, query: str) -> None:
        if query:
            self._search_query = query
            self._reload_articles()
            # 검색 결과가 없으면 안내 메시지 표시
            timeline = self.query_one(Timeline)
            if len(timeline) == 0:
                self.query_one(StatusBar).set_message(
                    t("search_no_results", query=query)
                )
            else:
                self.query_one(StatusBar).set_message(t("searching", query=query))
        else:
            self._search_query = None
            self.query_one(StatusBar).set_message("")
            self._reload_articles()

    def action_clear_search(self) -> None:
        """검색, 태그 필터, 피드 필터, 북마크 필터를 해제하고 원래 리스트로 복원."""
        if self._search_query is not None:
            self._search_query = None
            self.query_one(StatusBar).set_message(t("search_cleared"))
            self._reload_articles()
        elif self._tag_filter is not None:
            self._tag_filter = None
            self.query_one(StatusBar).set_message(t("tag_filter_cleared"))
            self._reload_articles()
        elif self._feed_filter is not None:
            self._feed_filter = None
            self.query_one(StatusBar).set_message(t("feed_filter_cleared"))
            self._reload_articles()
        elif self._bookmark_filter:
            self._bookmark_filter = False
            self.query_one(StatusBar).set_message("")
            self._reload_articles()

    def action_filter_bookmarks(self) -> None:
        self._bookmark_filter = not self._bookmark_filter
        status = self.query_one(StatusBar)
        if self._bookmark_filter:
            status.set_message(t("bookmarks_only"))
        else:
            status.set_message("")
        self._reload_articles()

    def action_add_feed(self) -> None:
        self.push_screen(AddFeedScreen(), self._on_add_feed_result)

    def _on_add_feed_result(self, result: tuple) -> None:
        if not result:
            return
        url, name = result
        feed = FeedConfig(url=url, name=name)
        # Save to config.yml
        add_feed(feed)
        # Also add to in-memory config
        if not any(f.url == url for f in self.config.feeds):
            self.config.feeds.append(feed)
        self.query_one(StatusBar).set_message(t("feed_added", name=name))
        # Fetch the new feed immediately
        self._do_refresh()

    def action_feed_list(self) -> None:
        """Open the feed list screen."""
        counts = self.db.get_article_count_by_feed()
        self.push_screen(
            FeedListScreen(self.config.feeds, counts),
            self._on_feed_list_result,
        )

    def _on_feed_list_result(self, feed_name: str | None) -> None:
        """피드 선택 결과로 필터를 적용한다."""
        if feed_name:
            self._feed_filter = feed_name
            self.query_one(StatusBar).set_message(t("feed_filter_active", name=feed_name))
            self._reload_articles()
        # None이면 아무 작업 안 함 (ESC/q로 닫은 경우)

    def _do_delete_feed(self, feed: FeedConfig) -> None:
        """피드를 config.yml과 DB에서 삭제하고 UI를 갱신한다."""
        # config.yml에서 제거
        remove_feed(feed.url)
        # 인메모리 config에서 제거
        self.config.feeds = [f for f in self.config.feeds if f.url != feed.url]
        # DB에서 해당 피드 글 삭제
        deleted_count = self.db.delete_articles_by_feed(feed.name)
        # 피드 필터가 삭제된 피드면 해제
        if self._feed_filter == feed.name:
            self._feed_filter = None
        # UI 갱신
        self.query_one(StatusBar).set_message(
            t("feed_deleted", name=feed.name, count=deleted_count)
        )
        self._reload_articles()

    def action_bookmark_list(self) -> None:
        """Open the bookmark list screen."""
        articles = self.db.get_articles(bookmarked_only=True)
        memos = self.db.get_all_bookmark_memos()
        tags = self.db.get_all_bookmark_tags()
        screen = BookmarkListScreen(articles, memos, tags)
        self.push_screen(screen, self._on_bookmark_list_result)
        if articles:
            self._generate_bookmark_analysis(screen, articles)

    @work(thread=True)
    def _generate_bookmark_analysis(
        self, screen: BookmarkListScreen, articles: list[Article]
    ) -> None:
        """북마크 컬렉션에 대한 AI 분석을 생성한다."""
        if not self.ai.is_available():
            self.call_from_thread(screen.update_analysis, t("claude_cli_not_found"))
            return

        from hawaiidisco.ai.prompts import (
            BOOKMARK_ANALYSIS_PROMPT,
            BOOKMARK_ANALYSIS_ITEM,
            NONE_TEXT,
            get_lang_name,
        )
        from hawaiidisco.i18n import get_lang

        lang = get_lang().value

        bookmarks_text = "\n".join(
            BOOKMARK_ANALYSIS_ITEM.format(
                title=a.title,
                description=a.description or NONE_TEXT,
                insight=a.insight or NONE_TEXT,
            )
            for a in articles
        )

        prompt = BOOKMARK_ANALYSIS_PROMPT.format(
            output_language=get_lang_name(lang),
            bookmarks=bookmarks_text,
        )

        result = self.ai.generate(prompt, timeout=60)
        try:
            status = self.query_one(StatusBar)
        except NoMatches:
            return
        if result:
            self.call_from_thread(screen.update_analysis, result)
            self.call_from_thread(status.set_message, t("bookmark_analysis_complete"))
        else:
            self.call_from_thread(screen.update_analysis, t("bookmark_analysis_failed"))
            self.call_from_thread(status.set_message, t("bookmark_analysis_failed"))

    def _on_bookmark_list_result(self, article_id: str | None) -> None:
        """Open the article selected from the bookmark list."""
        if not article_id:
            return
        article = self.db.get_article(article_id)
        if article:
            self._read_article(article)

    def action_import_opml(self) -> None:
        """OPML 파일에서 피드를 가져온다."""
        self.push_screen(OpmlImportScreen(), self._on_opml_import_result)

    def _on_opml_import_result(self, path_str: str) -> None:
        if not path_str:
            return
        try:
            path = Path(path_str).expanduser().resolve()
            feeds = parse_opml(path)
        except Exception as e:
            self.query_one(StatusBar).set_message(
                t("opml_import_error", error=type(e).__name__)
            )
            return

        if not feeds:
            self.query_one(StatusBar).set_message(t("opml_import_empty"))
            return

        added = 0
        for feed in feeds:
            if not any(f.url == feed.url for f in self.config.feeds):
                add_feed(feed)
                self.config.feeds.append(feed)
                added += 1

        self.query_one(StatusBar).set_message(
            t("opml_import_success", count=added)
        )
        if added > 0:
            self._do_refresh()

    def action_export_opml(self) -> None:
        """현재 피드 목록을 OPML 파일로 내보낸다."""
        if not self.config.feeds:
            self.query_one(StatusBar).set_message(t("opml_no_feeds"))
            return
        try:
            output_path = Path("~/.local/share/hawaiidisco/feeds.opml").expanduser()
            result_path = export_opml(self.config.feeds, output_path)
            self.query_one(StatusBar).set_message(
                t("opml_export_success", path=str(result_path))
            )
        except Exception as e:
            self.query_one(StatusBar).set_message(
                t("opml_export_error", error=type(e).__name__)
            )

    # --- Tag Actions ---

    def action_edit_tags(self) -> None:
        """북마크된 글에 태그를 편집한다."""
        article = self._get_current_article()
        if not article:
            return
        if not article.is_bookmarked:
            self.query_one(StatusBar).set_message(t("bookmark_first_for_tag"))
            return
        current_tags = self.db.get_bookmark_tags(article.id)
        self.push_screen(
            TagEditScreen(", ".join(current_tags)),
            self._on_tag_edit_result,
        )

    def _on_tag_edit_result(self, result: str) -> None:
        article = self._get_current_article()
        if not article or not result and result != "":
            return
        # result가 빈 문자열이면 dismiss(ESC) → 무시
        if result == "":
            return
        tags = [t_tag.strip() for t_tag in result.split(",") if t_tag.strip()]
        self.db.set_bookmark_tags(article.id, tags)
        self.query_one(StatusBar).set_message(t("tag_saved"))
        self._reload_articles()

    def action_tag_list(self) -> None:
        """태그 목록을 보여주고 선택하면 필터링한다."""
        all_tags = self.db.get_all_tags()
        if not all_tags:
            self.query_one(StatusBar).set_message(t("no_tags"))
            return
        # 각 태그별 글 수 계산
        tags_with_counts = [
            (tag, len(self.db.get_articles_by_tag(tag))) for tag in all_tags
        ]
        self.push_screen(
            TagListScreen(tags_with_counts),
            self._on_tag_list_result,
        )

    def _on_tag_list_result(self, tag: str | None) -> None:
        if tag:
            self._tag_filter = tag
            self.query_one(StatusBar).set_message(t("tag_filter_active", tag=tag))
            self._reload_articles()

    # --- Theme Actions ---

    def action_select_theme(self) -> None:
        """테마 선택 화면을 연다."""
        themes: list[tuple[str, bool]] = []
        for name, theme_obj in self.available_themes.items():
            if name == "textual-ansi":
                continue
            themes.append((name, theme_obj.dark))
        # 다크 테마를 먼저, 이름순 정렬
        themes.sort(key=lambda x: (not x[1], x[0]))
        self.push_screen(
            ThemeListScreen(themes, self.theme),
            self._on_theme_result,
        )

    def _on_theme_result(self, theme_name: str | None) -> None:
        if theme_name:
            self.theme = theme_name
            self.query_one(StatusBar).set_message(t("theme_applied", name=theme_name))

    def action_translate(self) -> None:
        """Translate the title/description of the selected article in the timeline."""
        article = self._get_current_article()
        if not article:
            return
        # Already translated
        if article.translated_title:
            self.query_one(StatusBar).set_message(t("already_translated"))
            return
        if not self.ai.is_available():
            self.query_one(StatusBar).set_message(t("claude_cli_not_found"))
            return
        self._do_translate(article)

    @work(thread=True)
    def _do_translate(self, article: Article) -> None:
        try:
            status = self.query_one(StatusBar)
        except NoMatches:
            return
        self.call_from_thread(status.set_message, t("translating"))

        t_title, t_desc = translate_article_meta(article.title, article.description, self.ai)
        self.db.set_translation(article.id, t_title, t_desc)

        self.call_from_thread(status.set_message, t("translated_preview", title=t_title[:40]))
        self.call_from_thread(self._reload_articles)

        updated = self.db.get_article(article.id)
        if updated:
            try:
                detail = self.query_one(DetailView)
                self.call_from_thread(detail.show_article, updated)
            except NoMatches:
                pass

    @work(thread=True)
    def _translate_article_body(self, screen: ArticleScreen) -> None:
        """Translate the article body for an ArticleScreen. Check DB cache first, generate if missing."""
        article_id = screen._article_id

        # Check DB cache
        if article_id:
            cached = self.db.get_translated_body(article_id)
            if cached:
                self.call_from_thread(screen.update_translated_body, cached)
                return

        # Generate translation
        translated = translate_text(screen._body, self.ai, timeout=60)
        if translated:
            # Save to DB
            if article_id:
                self.db.set_translated_body(article_id, translated)
            # Update UI (DOM access must happen inside call_from_thread callback)
            self.call_from_thread(screen.update_translated_body, translated)
        else:
            self.call_from_thread(
                screen.update_translated_body, t("translation_failed")
            )

    # --- Background Auto-Refresh ---

    def on_ready(self) -> None:
        """Set up the auto-refresh timer after the app is ready."""
        interval_seconds = self.config.refresh_interval * 60
        self.set_interval(interval_seconds, self._auto_refresh)

    def _auto_refresh(self) -> None:
        self._do_refresh()

    # --- Utilities ---

    def _get_current_article(self) -> Article | None:
        try:
            timeline = self.query_one(Timeline)
        except NoMatches:
            return None
        return timeline.get_highlighted_article()

    def _notify_macos(self, message: str) -> None:
        """Send a macOS notification."""
        # AppleScript 인젝션 방지: 백슬래시와 큰따옴표 이스케이프
        safe_msg = message.replace("\\", "\\\\").replace('"', '\\"')
        try:
            subprocess.Popen(
                [
                    "osascript", "-e",
                    f'display notification "{safe_msg}" with title "Hawaii Disco"',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, OSError):
            pass

    def on_unmount(self) -> None:
        self.db.close()


def main() -> None:
    app = HawaiiDiscoApp()
    app.run()


if __name__ == "__main__":
    main()
