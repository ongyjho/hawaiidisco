"""Feed management screens."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.css.query import NoMatches
from textual.widgets import Input, ListView, ListItem, Static

from hawaiidisco.config import FeedConfig
from hawaiidisco.i18n import t
from hawaiidisco.utils import _escape


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
