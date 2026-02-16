"""Unit tests for FeedListScreen, BookmarkListScreen, and BookmarkItem."""
from __future__ import annotations

from datetime import datetime

from hawaiidisco.config import FeedConfig
from hawaiidisco.db import Article
from hawaiidisco.app import FeedItem, FeedListScreen, BookmarkItem, BookmarkListScreen, TagItem


def _make_article(
    article_id: str = "test-1",
    title: str = "Test Article",
    feed_name: str = "TestFeed",
    published_at: datetime | None = None,
    memo: str | None = None,
) -> Article:
    return Article(
        id=article_id,
        feed_name=feed_name,
        title=title,
        link=f"https://example.com/{article_id}",
        description="desc",
        published_at=published_at or datetime(2025, 1, 15, 10, 0),
        fetched_at=datetime(2025, 1, 15, 10, 0),
        is_read=False,
        is_bookmarked=True,
        insight=None,
    )


class TestFeedItem:
    """Tests for FeedItem formatting."""

    def test_format_basic(self) -> None:
        """기본 포맷에 피드 이름, URL, 글 수가 포함된다."""
        feed = FeedConfig(url="https://a.com/feed", name="Feed A")
        item = FeedItem(feed, count=10)
        result = item._format()
        assert "Feed A" in result
        assert "https://a.com/feed" in result
        assert "10" in result

    def test_format_zero_count(self) -> None:
        """글 수가 0일 때도 정상 포맷된다."""
        feed = FeedConfig(url="https://new.com/feed", name="New Feed")
        item = FeedItem(feed, count=0)
        result = item._format()
        assert "New Feed" in result
        assert "0" in result


class TestFeedListScreen:
    """Tests for FeedListScreen initialization."""

    def test_init_with_feeds(self) -> None:
        """피드 데이터로 초기화된다."""
        feeds = [
            FeedConfig(url="https://a.com/feed", name="Feed A"),
            FeedConfig(url="https://b.com/feed", name="Feed B"),
        ]
        counts = {"Feed A": 10, "Feed B": 3}
        screen = FeedListScreen(feeds, counts)
        assert len(screen._feeds) == 2
        assert screen._counts == counts

    def test_init_empty(self) -> None:
        """빈 피드 리스트로 초기화된다."""
        screen = FeedListScreen([], {})
        assert len(screen._feeds) == 0


class TestBookmarkItem:
    """Tests for BookmarkItem formatting."""

    def test_format_basic(self) -> None:
        """Basic format includes title, feed name, and date."""
        article = _make_article()
        item = BookmarkItem(article)
        result = item._format()
        assert "Test Article" in result
        assert "TestFeed" in result
        assert "2025-01-15" in result

    def test_format_with_memo(self) -> None:
        """Show memo preview when memo is present."""
        article = _make_article()
        item = BookmarkItem(article, memo="좋은 글이다")
        result = item._format()
        assert "좋은 글이다" in result

    def test_format_long_memo_truncated(self) -> None:
        """Long memo is truncated with ellipsis."""
        article = _make_article()
        long_memo = "이것은 매우 긴 메모입니다. " * 10
        item = BookmarkItem(article, memo=long_memo)
        result = item._format()
        assert "..." in result

    def test_format_no_published_at(self) -> None:
        """Use fetched_at when published_at is None."""
        article = _make_article()
        article.published_at = None
        item = BookmarkItem(article)
        result = item._format()
        assert "2025-01-15" in result

    def test_format_with_tags(self) -> None:
        """태그가 있으면 표시된다."""
        article = _make_article()
        item = BookmarkItem(article, tags=["tech", "python"])
        result = item._format()
        assert "tech" in result
        assert "python" in result

    def test_format_without_tags(self) -> None:
        """태그가 없으면 태그 라인이 없다."""
        article = _make_article()
        item = BookmarkItem(article)
        result = item._format()
        assert "🏷" not in result


class TestBookmarkListScreen:
    """Tests for BookmarkListScreen initialization."""

    def test_init_with_articles(self) -> None:
        """Initialize with articles and memos."""
        articles = [_make_article("b-1"), _make_article("b-2")]
        memos = {"b-1": "메모1"}
        screen = BookmarkListScreen(articles, memos)
        assert len(screen._articles) == 2
        assert screen._memos == {"b-1": "메모1"}

    def test_init_empty(self) -> None:
        """Initialize with empty lists."""
        screen = BookmarkListScreen([], {})
        assert len(screen._articles) == 0
        assert screen._memos == {}


class TestTagItem:
    """Tests for TagItem formatting."""

    def test_format_basic(self) -> None:
        """기본 포맷에 태그 이름과 글 수가 포함된다."""
        item = TagItem("python", 5)
        result = item._format()
        assert "python" in result
        assert "5" in result

    def test_format_zero_count(self) -> None:
        """글 수가 0일 때도 정상 포맷된다."""
        item = TagItem("empty-tag", 0)
        result = item._format()
        assert "empty-tag" in result
        assert "0" in result

    def test_attributes(self) -> None:
        """TagItem에 tag와 count 속성이 올바르게 설정된다."""
        item = TagItem("tech", 10)
        assert item.tag == "tech"
        assert item._count == 10
