"""Status bar widget."""
from __future__ import annotations

from datetime import datetime

from textual.widgets import Static

from hawaiidisco.i18n import t


def _escape(text: str) -> str:
    """Escape Rich markup characters."""
    return text.replace("[", "\\[")


class StatusBar(Static):
    """Bottom status bar."""

    DEFAULT_CSS = """
    StatusBar {
        height: 2;
        padding: 0 1;
        background: $primary-background;
        color: $text;
        dock: bottom;
    }
    """

    def __init__(self) -> None:
        super().__init__("")
        self._message: str = ""
        self._last_refresh: datetime | None = None

    def set_message(self, message: str) -> None:
        """Display a temporary message."""
        self._message = message
        self._render_bar()

    def set_last_refresh(self, dt: datetime) -> None:
        self._last_refresh = dt
        self._render_bar()

    def _render_bar(self) -> None:
        groups = [
            # Navigation
            f"[dim]{t('nav_move')}[/]  [bold]Enter[/] [dim]{t('read')}[/]  [bold]o[/] [dim]{t('browser')}[/]",
            # 북마크/태그/읽음
            f"[bold]b[/] [dim]{t('bookmark')}[/]  [bold]R[/] [dim]{t('mark_read_label')}[/]  [bold]A[/] [dim]{t('mark_all_read_label')}[/]  [bold]u[/] [dim]{t('unread_label')}[/]  [bold]f[/] [dim]{t('filter')}[/]",
            # 콘텐츠
            f"[bold]r[/] [dim]{t('refresh')}[/]  [bold]t[/] [dim]{t('translate')}[/]  [bold]/[/] [dim]{t('search')}[/]  [bold]T[/] [dim]{t('tags_label')}[/]",
            # App
            f"[bold]a[/] [dim]{t('add_feed')}[/]  [bold]S[/] [dim]{t('theme_label')}[/]  [bold]q[/] [dim]{t('quit')}[/]",
        ]
        line1 = " " + " [dim]|[/] ".join(groups)

        if self._message:
            line2 = f" [bold yellow]{_escape(self._message)}[/]"
        elif self._last_refresh:
            line2 = f" [dim]{t('last_refresh', time=self._last_refresh.strftime('%H:%M:%S'))}[/]"
        else:
            line2 = ""

        self.update(f"{line1}\n{line2}")
