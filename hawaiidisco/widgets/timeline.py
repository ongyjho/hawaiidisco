"""Unified timeline widget."""
from __future__ import annotations

from datetime import datetime

from textual import events
from textual.binding import Binding
from textual.message import Message
from textual.widgets import ListView, ListItem, Static

from hawaiidisco.db import Article
from hawaiidisco.i18n import t
from hawaiidisco.utils import _escape


class ArticleItem(ListItem):
    """Individual article item in the timeline."""

    def __init__(self, article: Article, tags: list[str] | None = None) -> None:
        super().__init__()
        self.article = article
        self.tags = tags or []

    def _on_click(self, event: events.Click) -> None:
        """클릭 시 하이라이트만 이동, ListItem._on_click의 _ChildClicked 발생을 방지."""
        event.prevent_default()
        parent = self.parent
        if isinstance(parent, Timeline):
            parent.focus()
            if self in parent._nodes:
                parent.index = parent._nodes.index(self)

    def compose(self):
        yield ArticleRow(self.article, self.tags)


class ArticleRow(Static):
    """Single-row article display."""

    def __init__(self, article: Article, tags: list[str] | None = None) -> None:
        self.article = article
        self._tags = tags or []
        super().__init__(self._format())

    def _format(self) -> str:
        a = self.article
        lines = []

        # Status icon + title
        if a.is_bookmarked:
            icon = "[bold yellow]★[/] "
        elif a.is_read:
            icon = "[dim]○[/] "
        else:
            icon = "[bold green]●[/] "

        title_style = "dim" if a.is_read and not a.is_bookmarked else "bold"
        lines.append(f"{icon}[{title_style}]{_escape(a.title)}[/]")

        # Show translated title if available
        if a.translated_title:
            lines.append(f"  [italic magenta]{_escape(a.translated_title)}[/]")

        # Feed name + time
        time_str = _relative_time(a.published_at or a.fetched_at)
        lines.append(f"  [cyan]{_escape(a.feed_name)}[/] · [dim]{time_str}[/]")

        # 태그 표시
        if self._tags:
            lines.append(f"  [dim]🏷 {_escape(', '.join(self._tags))}[/]")

        # Show insight if available
        if a.insight:
            preview = a.insight if len(a.insight) <= 60 else a.insight[:57] + "..."
            lines.append(f"  [italic dim]💡 {_escape(preview)}[/]")

        return "\n".join(lines)


class Timeline(ListView):
    """Unified timeline list view."""

    BINDINGS = [
        Binding("k", "cursor_up", "Up", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("space", "select_cursor", "Select", show=False),
    ]

    class ArticleSelected(Message):
        """Article selected."""
        def __init__(self, article: Article) -> None:
            super().__init__()
            self.article = article

    class ArticleHighlighted(Message):
        """Article highlighted."""
        def __init__(self, article: Article) -> None:
            super().__init__()
            self.article = article

    def __init__(self, articles: list[Article] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._articles = articles or []

    def compose(self):
        for article in self._articles:
            yield ArticleItem(article)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, ArticleItem):
            self.post_message(self.ArticleSelected(event.item.article))

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item and isinstance(event.item, ArticleItem):
            self.post_message(self.ArticleHighlighted(event.item.article))

    def refresh_articles(
        self,
        articles: list[Article],
        tags: dict[str, list[str]] | None = None,
    ) -> None:
        """Refresh the article list."""
        # 이전 하이라이트 위치 저장
        highlighted = self.get_highlighted_article()
        current_id = highlighted.id if highlighted else None

        self._articles = articles
        tags = tags or {}
        self.clear()
        for article in articles:
            self.append(ArticleItem(article, tags.get(article.id)))

        # 이전 하이라이트 위치 복원
        if current_id:
            for i, article in enumerate(articles):
                if article.id == current_id:
                    self.index = i
                    break

    def get_highlighted_article(self) -> Article | None:
        """Return the currently highlighted article."""
        if self.highlighted_child and isinstance(self.highlighted_child, ArticleItem):
            return self.highlighted_child.article
        return None


def _relative_time(dt: datetime) -> str:
    """Generate a relative time string."""
    now = datetime.now()
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 0:
        return t("just_now")
    if seconds < 60:
        return t("just_now")
    if seconds < 3600:
        return t("minutes_ago", n=seconds // 60)
    if seconds < 86400:
        return t("hours_ago", n=seconds // 3600)
    if seconds < 604800:
        return t("days_ago", n=seconds // 86400)
    return dt.strftime("%m/%d")
