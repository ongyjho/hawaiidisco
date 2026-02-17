"""Tests for shared markdown rendering utilities."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from hawaiidisco.db import Article
from hawaiidisco.md_render import article_date_str, feed_subfolder_name, safe_path, slugify


def _make_article(**kwargs: object) -> Article:
    defaults: dict = {
        "id": "test-1",
        "feed_name": "HackerNews",
        "title": "Test Article",
        "link": "https://example.com",
        "description": "desc",
        "published_at": datetime(2025, 2, 16),
        "fetched_at": datetime(2025, 2, 16, 12, 0),
        "is_read": False,
        "is_bookmarked": False,
        "insight": None,
    }
    defaults.update(kwargs)
    return Article(**defaults)


class TestSlugify:
    def test_basic(self) -> None:
        assert slugify("Hello World") == "Hello-World"

    def test_korean_preserved(self) -> None:
        assert "한글" in slugify("한글 테스트")

    def test_special_chars_removed(self) -> None:
        result = slugify("Hello! @World# $%")
        assert "!" not in result
        assert "@" not in result

    def test_max_len(self) -> None:
        assert len(slugify("a" * 100, max_len=30)) <= 30

    def test_path_traversal_chars_removed(self) -> None:
        result = slugify("../../etc/passwd")
        assert "/" not in result


class TestSafePath:
    def test_normal(self, tmp_path: Path) -> None:
        result = safe_path(tmp_path, "test.md")
        assert result == (tmp_path / "test.md").resolve()

    def test_traversal_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Path traversal"):
            safe_path(tmp_path, "../../../etc/passwd")

    def test_subdirectory_allowed(self, tmp_path: Path) -> None:
        result = safe_path(tmp_path, "sub/test.md")
        assert result.is_relative_to(tmp_path.resolve())


class TestArticleDateStr:
    def test_uses_published_at(self) -> None:
        article = _make_article(published_at=datetime(2025, 3, 1))
        assert article_date_str(article) == "2025-03-01"

    def test_falls_back_to_fetched_at(self) -> None:
        article = _make_article(published_at=None, fetched_at=datetime(2025, 4, 15, 10, 0))
        assert article_date_str(article) == "2025-04-15"


class TestFeedSubfolderName:
    def test_basic(self) -> None:
        assert feed_subfolder_name("HackerNews") == "HackerNews"

    def test_spaces_replaced(self) -> None:
        assert feed_subfolder_name("Hacker News") == "Hacker-News"

    def test_special_chars_removed(self) -> None:
        result = feed_subfolder_name("Feed/Name@#!")
        assert "/" not in result
        assert "@" not in result

    def test_empty_becomes_unknown(self) -> None:
        assert feed_subfolder_name("   ") == "unknown"

    def test_korean_preserved(self) -> None:
        assert "긱뉴스" in feed_subfolder_name("긱뉴스")
