"""Tests for Database thread safety and translated_body."""
from __future__ import annotations

import threading
from pathlib import Path

import pytest

from hawaiidisco.db import Database


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    """Create a temporary DB instance."""
    return Database(tmp_path / "test.db")


def _insert_sample(db: Database, article_id: str = "test-1") -> None:
    """Insert a sample article for testing."""
    db.upsert_article(
        article_id=article_id,
        feed_name="TestFeed",
        title="Test Article",
        link="https://example.com",
        description="desc",
        published_at=None,
    )


class TestThreadSafety:
    """DB access from different threads should not raise ProgrammingError."""

    def test_read_from_other_thread(self, db: Database) -> None:
        """DB created in the main thread can be read from another thread."""
        results: list = []
        errors: list[Exception] = []

        def worker() -> None:
            try:
                articles = db.get_articles()
                results.append(articles)
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert not errors, f"Error occurred in thread: {errors[0]}"
        assert results[0] == []

    def test_write_from_other_thread(self, db: Database) -> None:
        """DB can be written to from another thread."""
        errors: list[Exception] = []

        def worker() -> None:
            try:
                db.upsert_article(
                    article_id="test-1",
                    feed_name="TestFeed",
                    title="Test Article",
                    link="https://example.com",
                    description="desc",
                    published_at=None,
                )
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert not errors, f"Error occurred in thread: {errors[0]}"
        # retrieve data written by another thread from the main thread
        article = db.get_article("test-1")
        assert article is not None
        assert article.title == "Test Article"

    def test_concurrent_read_write(self, db: Database) -> None:
        """No errors when multiple threads perform concurrent reads and writes."""
        errors: list[Exception] = []
        count = 20

        def writer(i: int) -> None:
            try:
                db.upsert_article(
                    article_id=f"concurrent-{i}",
                    feed_name="TestFeed",
                    title=f"Article {i}",
                    link=f"https://example.com/{i}",
                    description=None,
                    published_at=None,
                )
            except Exception as e:
                errors.append(e)

        def reader() -> None:
            try:
                db.get_articles()
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(count):
            threads.append(threading.Thread(target=writer, args=(i,)))
            threads.append(threading.Thread(target=reader))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Concurrent access error: {errors}"

class TestTranslatedBody:
    """Tests for translated_body column migration and CRUD."""

    def test_migration_adds_translated_body_column(self, tmp_path: Path) -> None:
        """Migration adds the translated_body column."""
        db = Database(tmp_path / "migrate.db")
        conn = db._get_conn()
        cursor = conn.execute("PRAGMA table_info(articles)")
        columns = {row[1] for row in cursor.fetchall()}
        assert "translated_body" in columns

    def test_new_article_has_null_translated_body(self, db: Database) -> None:
        """New article's translated_body is None."""
        _insert_sample(db)
        article = db.get_article("test-1")
        assert article is not None
        assert article.translated_body is None

    def test_set_and_get_translated_body(self, db: Database) -> None:
        """Save and retrieve translated_body."""
        _insert_sample(db)
        db.set_translated_body("test-1", "번역된 본문입니다")
        body = db.get_translated_body("test-1")
        assert body == "번역된 본문입니다"

    def test_get_translated_body_returns_none_for_missing(self, db: Database) -> None:
        """Nonexistent article_id returns None."""
        body = db.get_translated_body("nonexistent")
        assert body is None

    def test_translated_body_in_get_article(self, db: Database) -> None:
        """Article retrieved via get_article includes translated_body."""
        _insert_sample(db)
        db.set_translated_body("test-1", "번역된 본문")
        article = db.get_article("test-1")
        assert article is not None
        assert article.translated_body == "번역된 본문"

    def test_translated_body_in_get_articles(self, db: Database) -> None:
        """Article list retrieved via get_articles includes translated_body."""
        _insert_sample(db)
        db.set_translated_body("test-1", "번역 목록 테스트")
        articles = db.get_articles()
        assert len(articles) == 1
        assert articles[0].translated_body == "번역 목록 테스트"

    def test_set_translated_body_from_other_thread(self, db: Database) -> None:
        """translated_body can be saved from another thread."""
        _insert_sample(db)
        errors: list[Exception] = []

        def worker() -> None:
            try:
                db.set_translated_body("test-1", "스레드 번역")
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert not errors, f"Error occurred in thread: {errors[0]}"
        body = db.get_translated_body("test-1")
        assert body == "스레드 번역"


class TestArticleCountByFeed:
    """Tests for article count per feed."""

    def test_empty_db_returns_empty_dict(self, db: Database) -> None:
        """Empty DB returns an empty dict."""
        result = db.get_article_count_by_feed()
        assert result == {}

    def test_single_feed_count(self, db: Database) -> None:
        """Return article count for a single feed."""
        _insert_sample(db, "a-1")
        _insert_sample(db, "a-2")
        result = db.get_article_count_by_feed()
        assert result == {"TestFeed": 2}

    def test_multiple_feeds_count(self, db: Database) -> None:
        """Return article counts for multiple feeds."""
        db.upsert_article("a-1", "Feed A", "Article 1", "https://a.com/1", None, None)
        db.upsert_article("a-2", "Feed A", "Article 2", "https://a.com/2", None, None)
        db.upsert_article("b-1", "Feed B", "Article 3", "https://b.com/1", None, None)
        result = db.get_article_count_by_feed()
        assert result == {"Feed A": 2, "Feed B": 1}


class TestDeleteArticlesByFeed:
    """Tests for delete_articles_by_feed."""

    def test_delete_articles(self, db: Database) -> None:
        """Deletes all articles for a specific feed."""
        db.upsert_article("d-1", "Feed A", "A1", "https://a.com/1", None, None)
        db.upsert_article("d-2", "Feed A", "A2", "https://a.com/2", None, None)
        db.upsert_article("d-3", "Feed B", "B1", "https://b.com/1", None, None)
        deleted = db.delete_articles_by_feed("Feed A")
        assert deleted == 2
        remaining = db.get_articles()
        assert len(remaining) == 1
        assert remaining[0].feed_name == "Feed B"

    def test_delete_cascade_bookmarks(self, db: Database) -> None:
        """Deleting a feed also deletes its article bookmarks."""
        db.upsert_article("d-4", "Feed X", "X1", "https://x.com/1", None, None)
        db.toggle_bookmark("d-4")
        db.set_bookmark_memo("d-4", "메모")
        deleted = db.delete_articles_by_feed("Feed X")
        assert deleted == 1
        # Verify bookmarks were also deleted
        assert db.get_bookmark_memo("d-4") is None

    def test_delete_nonexistent_feed(self, db: Database) -> None:
        """Deleting a non-existent feed returns 0."""
        deleted = db.delete_articles_by_feed("Nonexistent")
        assert deleted == 0


class TestFeedNameFilter:
    """Tests for get_articles feed_name filter."""

    def test_filter_by_feed_name(self, db: Database) -> None:
        """Filters articles by feed_name."""
        db.upsert_article("f-1", "Feed A", "Article 1", "https://a.com/1", None, None)
        db.upsert_article("f-2", "Feed B", "Article 2", "https://b.com/1", None, None)
        db.upsert_article("f-3", "Feed A", "Article 3", "https://a.com/2", None, None)
        results = db.get_articles(feed_name="Feed A")
        assert len(results) == 2
        assert all(a.feed_name == "Feed A" for a in results)

    def test_filter_no_match(self, db: Database) -> None:
        """Filtering by a non-existent feed name returns an empty list."""
        _insert_sample(db, "f-4")
        results = db.get_articles(feed_name="Nonexistent")
        assert results == []

    def test_filter_none_returns_all(self, db: Database) -> None:
        """Returns all articles when feed_name is None."""
        db.upsert_article("f-5", "Feed A", "A1", "https://a.com/1", None, None)
        db.upsert_article("f-6", "Feed B", "B1", "https://b.com/1", None, None)
        results = db.get_articles(feed_name=None)
        assert len(results) == 2

    def test_filter_with_search_combined(self, db: Database) -> None:
        """feed_name and search can be combined."""
        db.upsert_article("f-7", "Feed A", "Python Tips", "https://a.com/1", None, None)
        db.upsert_article("f-8", "Feed A", "Rust Tips", "https://a.com/2", None, None)
        db.upsert_article("f-9", "Feed B", "Python Guide", "https://b.com/1", None, None)
        results = db.get_articles(feed_name="Feed A", search="Python")
        assert len(results) == 1
        assert results[0].id == "f-7"


class TestUnreadFilter:
    """Tests for get_articles unread_only filter."""

    def test_unread_only_returns_unread(self, db: Database) -> None:
        """unread_only=True는 읽지 않은 글만 반환한다."""
        db.upsert_article("u-1", "Feed A", "Unread Article", "https://a.com/1", None, None)
        db.upsert_article("u-2", "Feed A", "Read Article", "https://a.com/2", None, None)
        db.mark_read("u-2")
        results = db.get_articles(unread_only=True)
        assert len(results) == 1
        assert results[0].id == "u-1"
        assert not results[0].is_read

    def test_unread_only_false_returns_all(self, db: Database) -> None:
        """unread_only=False(기본값)는 모든 글을 반환한다."""
        db.upsert_article("u-3", "Feed A", "Article 1", "https://a.com/1", None, None)
        db.upsert_article("u-4", "Feed A", "Article 2", "https://a.com/2", None, None)
        db.mark_read("u-4")
        results = db.get_articles(unread_only=False)
        assert len(results) == 2

    def test_unread_with_feed_filter(self, db: Database) -> None:
        """unread_only와 feed_name 필터를 조합할 수 있다."""
        db.upsert_article("u-5", "Feed A", "A Unread", "https://a.com/1", None, None)
        db.upsert_article("u-6", "Feed A", "A Read", "https://a.com/2", None, None)
        db.upsert_article("u-7", "Feed B", "B Unread", "https://b.com/1", None, None)
        db.mark_read("u-6")
        results = db.get_articles(feed_name="Feed A", unread_only=True)
        assert len(results) == 1
        assert results[0].id == "u-5"

    def test_unread_with_search(self, db: Database) -> None:
        """unread_only와 search를 조합할 수 있다."""
        db.upsert_article("u-8", "Feed A", "Python Tips", "https://a.com/1", None, None)
        db.upsert_article("u-9", "Feed A", "Python Guide", "https://a.com/2", None, None)
        db.upsert_article("u-10", "Feed A", "Rust Guide", "https://a.com/3", None, None)
        db.mark_read("u-9")
        results = db.get_articles(search="Python", unread_only=True)
        assert len(results) == 1
        assert results[0].id == "u-8"

    def test_unread_with_bookmarked(self, db: Database) -> None:
        """unread_only와 bookmarked_only를 조합할 수 있다."""
        db.upsert_article("u-11", "Feed A", "BM Unread", "https://a.com/1", None, None)
        db.upsert_article("u-12", "Feed A", "BM Read", "https://a.com/2", None, None)
        db.upsert_article("u-13", "Feed A", "Not BM", "https://a.com/3", None, None)
        db.toggle_bookmark("u-11")
        db.toggle_bookmark("u-12")
        db.mark_read("u-12")
        results = db.get_articles(bookmarked_only=True, unread_only=True)
        assert len(results) == 1
        assert results[0].id == "u-11"

    def test_all_read_returns_empty(self, db: Database) -> None:
        """모든 글이 읽힌 상태에서 unread_only=True는 빈 리스트를 반환한다."""
        db.upsert_article("u-14", "Feed A", "Article", "https://a.com/1", None, None)
        db.mark_read("u-14")
        results = db.get_articles(unread_only=True)
        assert results == []


class TestGetAllBookmarkMemos:
    """Tests for retrieving all bookmark memos."""

    def test_empty_returns_empty_dict(self, db: Database) -> None:
        """Return an empty dict when there are no bookmarks."""
        result = db.get_all_bookmark_memos()
        assert result == {}

    def test_bookmarks_with_memo(self, db: Database) -> None:
        """Return only bookmarks that have a memo."""
        _insert_sample(db, "m-1")
        db.toggle_bookmark("m-1")
        db.set_bookmark_memo("m-1", "좋은 글")
        result = db.get_all_bookmark_memos()
        assert result == {"m-1": "좋은 글"}

    def test_empty_memo_excluded(self, db: Database) -> None:
        """Empty string memos are excluded from results."""
        _insert_sample(db, "m-2")
        db.toggle_bookmark("m-2")
        db.set_bookmark_memo("m-2", "")
        result = db.get_all_bookmark_memos()
        assert result == {}

    def test_no_memo_bookmark_excluded(self, db: Database) -> None:
        """Bookmarks without a memo are excluded from results."""
        _insert_sample(db, "m-3")
        db.toggle_bookmark("m-3")
        # no memo set
        result = db.get_all_bookmark_memos()
        assert result == {}


class TestBookmarkTags:
    """Tests for bookmark tag CRUD."""

    def test_set_and_get_tags(self, db: Database) -> None:
        """Tags can be saved and retrieved."""
        _insert_sample(db, "tag-1")
        db.toggle_bookmark("tag-1")
        db.set_bookmark_tags("tag-1", ["tech", "python"])
        tags = db.get_bookmark_tags("tag-1")
        assert tags == ["tech", "python"]

    def test_get_tags_empty_default(self, db: Database) -> None:
        """Returns an empty list when no tags exist."""
        _insert_sample(db, "tag-2")
        db.toggle_bookmark("tag-2")
        tags = db.get_bookmark_tags("tag-2")
        assert tags == []

    def test_set_empty_tags_clears(self, db: Database) -> None:
        """Setting an empty list removes tags."""
        _insert_sample(db, "tag-3")
        db.toggle_bookmark("tag-3")
        db.set_bookmark_tags("tag-3", ["tech"])
        db.set_bookmark_tags("tag-3", [])
        tags = db.get_bookmark_tags("tag-3")
        assert tags == []

    def test_get_tags_nonexistent_article(self, db: Database) -> None:
        """Non-existent article_id returns an empty list."""
        tags = db.get_bookmark_tags("nonexistent")
        assert tags == []

    def test_get_all_tags(self, db: Database) -> None:
        """Returns all unique tags sorted."""
        _insert_sample(db, "tag-a1")
        db.toggle_bookmark("tag-a1")
        db.set_bookmark_tags("tag-a1", ["python", "tech"])

        _insert_sample(db, "tag-a2")
        db.toggle_bookmark("tag-a2")
        db.set_bookmark_tags("tag-a2", ["rust", "tech"])

        all_tags = db.get_all_tags()
        assert all_tags == ["python", "rust", "tech"]

    def test_get_all_tags_empty(self, db: Database) -> None:
        """Returns an empty list when no tags exist."""
        assert db.get_all_tags() == []

    def test_get_articles_by_tag(self, db: Database) -> None:
        """Returns only articles with the given tag."""
        _insert_sample(db, "tag-b1")
        db.toggle_bookmark("tag-b1")
        db.set_bookmark_tags("tag-b1", ["python", "tech"])

        _insert_sample(db, "tag-b2")
        db.toggle_bookmark("tag-b2")
        db.set_bookmark_tags("tag-b2", ["rust"])

        _insert_sample(db, "tag-b3")
        db.toggle_bookmark("tag-b3")
        db.set_bookmark_tags("tag-b3", ["tech"])

        python_articles = db.get_articles_by_tag("python")
        assert len(python_articles) == 1
        assert python_articles[0].id == "tag-b1"

        tech_articles = db.get_articles_by_tag("tech")
        assert len(tech_articles) == 2

    def test_get_articles_by_tag_no_partial_match(self, db: Database) -> None:
        """Partial substring matching does not occur."""
        _insert_sample(db, "tag-c1")
        db.toggle_bookmark("tag-c1")
        db.set_bookmark_tags("tag-c1", ["python"])

        # Searching for "py" should not match
        results = db.get_articles_by_tag("py")
        assert len(results) == 0

    def test_get_articles_by_tag_single_tag(self, db: Database) -> None:
        """Single tag (no comma) is matched exactly."""
        _insert_sample(db, "tag-d1")
        db.toggle_bookmark("tag-d1")
        db.set_bookmark_tags("tag-d1", ["solo"])

        results = db.get_articles_by_tag("solo")
        assert len(results) == 1

    def test_get_all_bookmark_tags(self, db: Database) -> None:
        """Returns all bookmark tags as a dict."""
        _insert_sample(db, "tag-e1")
        db.toggle_bookmark("tag-e1")
        db.set_bookmark_tags("tag-e1", ["ai", "ml"])

        _insert_sample(db, "tag-e2")
        db.toggle_bookmark("tag-e2")
        # No tags

        result = db.get_all_bookmark_tags()
        assert result == {"tag-e1": ["ai", "ml"]}


class TestGetRecentBookmarkedArticles:
    """Tests for querying recently bookmarked articles."""

    def test_empty_returns_empty_list(self, db: Database) -> None:
        """Returns an empty list when no bookmarks exist."""
        result = db.get_recent_bookmarked_articles(days=7)
        assert result == []

    def test_recent_bookmark_returned(self, db: Database) -> None:
        """Recently bookmarked article is returned."""
        _insert_sample(db, "r-1")
        db.toggle_bookmark("r-1")
        result = db.get_recent_bookmarked_articles(days=7)
        assert len(result) == 1
        assert result[0].id == "r-1"

    def test_unbookmarked_article_excluded(self, db: Database) -> None:
        """Non-bookmarked articles are excluded."""
        _insert_sample(db, "r-2")
        result = db.get_recent_bookmarked_articles(days=7)
        assert result == []

    def test_multiple_bookmarks_ordered_desc(self, db: Database) -> None:
        """Multiple bookmarks are returned in descending order."""
        for i in range(3):
            _insert_sample(db, f"r-{i}")
            db.toggle_bookmark(f"r-{i}")
        result = db.get_recent_bookmarked_articles(days=7)
        assert len(result) == 3
        # Last bookmarked item comes first
        assert result[0].id == "r-2"

    def test_from_other_thread(self, db: Database) -> None:
        """Can be queried from another thread."""
        _insert_sample(db, "r-t")
        db.toggle_bookmark("r-t")
        errors: list[Exception] = []
        results: list = []

        def worker() -> None:
            try:
                results.extend(db.get_recent_bookmarked_articles(days=7))
            except Exception as e:
                errors.append(e)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert not errors, f"Error in thread: {errors[0]}"
        assert len(results) == 1
