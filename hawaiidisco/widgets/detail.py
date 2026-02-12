"""Article detail view widget."""
from __future__ import annotations

from textual.widgets import Static

from hawaiidisco.db import Article
from hawaiidisco.i18n import t


def _escape(text: str) -> str:
    """Escape Rich markup characters."""
    return text.replace("[", "\\[")


class DetailView(Static):
    """Display detailed information for the selected article."""

    DEFAULT_CSS = """
    DetailView {
        height: auto;
        max-height: 12;
        padding: 1 2;
        background: $surface;
        border-top: solid $primary;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._article: Article | None = None

    def show_article(self, article: Article) -> None:
        self._article = article
        self.update(self._format())

    def _format(self) -> str:
        a = self._article
        if not a:
            return t("select_article")

        lines = []
        lines.append(f"[bold]{_escape(a.title)}[/]")
        if a.translated_title:
            lines.append(f"[italic magenta]{_escape(a.translated_title)}[/]")
        date_str = a.published_at.strftime('%Y-%m-%d %H:%M') if a.published_at else ""
        lines.append(f"[cyan]{_escape(a.feed_name)}[/] · [dim]{date_str}[/]")
        lines.append(f"[underline blue]{_escape(a.link)}[/]")

        if a.translated_desc:
            lines.append("")
            lines.append(f"[magenta]{_escape(a.translated_desc)}[/]")
        elif a.description:
            desc = a.description if len(a.description) <= 300 else a.description[:297] + "..."
            lines.append("")
            lines.append(f"[dim]{_escape(desc)}[/]")

        if a.insight:
            lines.append("")
            lines.append(f"[yellow]💡[/] [italic]{_escape(a.insight)}[/]")

        return "\n".join(lines)

    def clear_detail(self) -> None:
        self._article = None
        self.update("")
