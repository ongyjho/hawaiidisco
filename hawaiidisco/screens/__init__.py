"""Screen classes for Hawaii Disco TUI."""
from __future__ import annotations

from hawaiidisco.screens.memo import MemoScreen
from hawaiidisco.screens.article import ArticleScreen
from hawaiidisco.screens.feed import AddFeedScreen, ConfirmDeleteScreen, FeedItem, FeedListScreen
from hawaiidisco.screens.bookmark import BookmarkItem, BookmarkListScreen
from hawaiidisco.screens.search import SearchScreen
from hawaiidisco.screens.tag import TagEditScreen, TagItem, TagListScreen
from hawaiidisco.screens.theme import ThemeItem, ThemeListScreen
from hawaiidisco.screens.opml_import import OpmlImportScreen
from hawaiidisco.screens.digest import DigestScreen

__all__ = [
    "MemoScreen",
    "ArticleScreen",
    "AddFeedScreen",
    "ConfirmDeleteScreen",
    "FeedItem",
    "FeedListScreen",
    "BookmarkItem",
    "BookmarkListScreen",
    "SearchScreen",
    "TagEditScreen",
    "TagItem",
    "TagListScreen",
    "ThemeItem",
    "ThemeListScreen",
    "OpmlImportScreen",
    "DigestScreen",
]
