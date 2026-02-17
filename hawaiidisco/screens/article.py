"""Article body viewer screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.css.query import NoMatches
from textual.widgets import Static, TabbedContent, TabPane

from hawaiidisco.i18n import t
from hawaiidisco.utils import _escape


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
