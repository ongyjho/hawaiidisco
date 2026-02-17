"""Integration tests for cross-module workflows."""
from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.config import (
    Config,
    DigestConfig,
    ObsidianConfig,
    ensure_dirs,
    load_config,
)
from hawaiidisco.db import Article, Database
from hawaiidisco.digest import get_or_generate_digest
from hawaiidisco.insight import get_or_generate_insight
from hawaiidisco.obsidian import save_digest_note, save_obsidian_note
from hawaiidisco.translate import translate_text


# --- Shared fixtures ---


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    return Database(tmp_path / "test.db")


@pytest.fixture()
def obsidian_config(tmp_path: Path) -> ObsidianConfig:
    vault = tmp_path / "vault"
    vault.mkdir()
    return ObsidianConfig(
        enabled=True,
        vault_path=vault,
        folder="hawaii-disco",
    )


def _make_article(
    article_id: str = "test-1",
    title: str = "Test Article",
    feed_name: str = "TestFeed",
    published_at: datetime | None = None,
    description: str | None = "Test description",
    insight: str | None = None,
    is_bookmarked: bool = False,
) -> Article:
    return Article(
        id=article_id,
        feed_name=feed_name,
        title=title,
        link=f"https://example.com/{article_id}",
        description=description,
        published_at=published_at or datetime(2025, 1, 15, 10, 0),
        fetched_at=datetime(2025, 1, 15, 10, 0),
        is_read=False,
        is_bookmarked=is_bookmarked,
        insight=insight,
    )


def _mock_provider(response: str | None = "AI response") -> MagicMock:
    provider = MagicMock(spec=AIProvider)
    provider.is_available.return_value = True
    provider.generate.return_value = response
    provider.name = "mock"
    return provider


def _insert_article(db: Database, article: Article) -> None:
    """Insert an article into the DB for testing."""
    db.upsert_article(
        article.id,
        article.feed_name,
        article.title,
        article.link,
        article.description,
        article.published_at,
    )
    if article.insight:
        db.set_insight(article.id, article.insight)
    if article.is_bookmarked:
        db.toggle_bookmark(article.id)


# --- Test Classes ---


class TestFeedToDBFlow:
    """Feed fetch → DB upsert → article retrieval."""

    def test_mock_feed_to_db(self, db: Database) -> None:
        """Simulate feed fetch by inserting articles and verifying DB storage."""
        feeds_data = [
            ("art-1", "Feed A", "Article One"),
            ("art-2", "Feed A", "Article Two"),
            ("art-3", "Feed B", "Article Three"),
        ]
        for aid, fname, title in feeds_data:
            db.upsert_article(aid, fname, title, f"https://x.com/{aid}", "desc", datetime.now())

        articles = db.get_articles()
        assert len(articles) == 3

        # Feed name filter
        feed_a = db.get_articles(feed_name="Feed A")
        assert len(feed_a) == 2
        assert all(a.feed_name == "Feed A" for a in feed_a)

    def test_duplicate_upsert_ignored(self, db: Database) -> None:
        """Duplicate article IDs should be ignored."""
        db.upsert_article("dup-1", "Feed", "Title", "https://x.com/1", "desc", datetime.now())
        inserted = db.upsert_article("dup-1", "Feed", "Title", "https://x.com/1", "desc", datetime.now())
        assert inserted is False
        assert len(db.get_articles()) == 1

    def test_article_count_by_feed(self, db: Database) -> None:
        """Article count per feed is accurate."""
        for i in range(5):
            db.upsert_article(f"a-{i}", "Alpha", f"Title {i}", f"https://x.com/{i}", None, datetime.now())
        for i in range(3):
            db.upsert_article(f"b-{i}", "Beta", f"Title {i}", f"https://x.com/b{i}", None, datetime.now())

        counts = db.get_article_count_by_feed()
        assert counts["Alpha"] == 5
        assert counts["Beta"] == 3


class TestArticleInsightFlow:
    """Article → AI insight generation → DB cache → re-read cache hit."""

    def test_generate_and_cache_insight(self, db: Database) -> None:
        """Generate insight, save to DB, and verify cache hit on re-read."""
        article = _make_article(article_id="ins-1")
        _insert_article(db, article)

        provider = _mock_provider("This is a sharp insight about the article.")

        # First call: generates insight
        result = get_or_generate_insight(article, db, provider)
        assert result == "This is a sharp insight about the article."
        assert provider.generate.call_count == 1

        # Verify DB cache
        cached = db.get_article("ins-1")
        assert cached is not None
        assert cached.insight == "This is a sharp insight about the article."

        # Second call with updated article: should use cache
        result2 = get_or_generate_insight(cached, db, provider)
        assert result2 == cached.insight
        # generate should NOT be called again (cache hit)
        assert provider.generate.call_count == 1

    def test_provider_unavailable(self, db: Database) -> None:
        """When provider is unavailable, return fallback message."""
        article = _make_article()
        _insert_article(db, article)

        provider = _mock_provider()
        provider.is_available.return_value = False

        result = get_or_generate_insight(article, db, provider)
        assert "CLI" in result or "not found" in result.lower() or "찾을" in result


class TestArticleTranslationFlow:
    """Article body → AI translation → DB cache → cache hit on re-call."""

    def test_translate_and_cache(self, db: Database) -> None:
        """Translate body, save to DB, re-read cache."""
        article = _make_article(article_id="trans-1")
        _insert_article(db, article)

        provider = _mock_provider("번역된 본문입니다.")

        # Translate
        result = translate_text("English body text", provider, lang="ko")
        assert result == "번역된 본문입니다."

        # Save to DB
        db.set_translated_body("trans-1", result)

        # Re-read from DB
        cached = db.get_translated_body("trans-1")
        assert cached == "번역된 본문입니다."

    def test_translate_english_skips(self) -> None:
        """English user should skip translation."""
        provider = _mock_provider()
        result = translate_text("Hello world", provider, lang="en")
        assert result is None
        provider.generate.assert_not_called()


class TestBookmarkObsidianFlow:
    """Bookmark → save MD → Obsidian note → verify file content."""

    def test_bookmark_to_obsidian(self, db: Database, obsidian_config: ObsidianConfig) -> None:
        """Bookmark article → save to Obsidian → verify file structure."""
        article = _make_article(article_id="bm-1", insight="Great insight")
        _insert_article(db, article)

        # Bookmark
        db.toggle_bookmark("bm-1")
        updated = db.get_article("bm-1")
        assert updated is not None
        assert updated.is_bookmarked is True

        # Save to Obsidian
        filepath = save_obsidian_note(updated, obsidian_config, memo="My notes", tags=["tech"])
        assert filepath.exists()

        content = filepath.read_text(encoding="utf-8")
        assert "---" in content  # Frontmatter
        assert "Test Article" in content
        assert "Great insight" in content
        assert "My notes" in content
        assert "tech" in content

    def test_bookmark_unbookmark_cycle(self, db: Database) -> None:
        """Bookmark and unbookmark an article."""
        article = _make_article(article_id="cycle-1")
        _insert_article(db, article)

        # Bookmark
        assert db.toggle_bookmark("cycle-1") is True
        # Unbookmark
        assert db.toggle_bookmark("cycle-1") is False

        refreshed = db.get_article("cycle-1")
        assert refreshed is not None
        assert refreshed.is_bookmarked is False


class TestDigestFlow:
    """Insert articles → generate digest → DB cache → Obsidian save."""

    def test_generate_and_cache_digest(self, db: Database) -> None:
        """Generate digest from recent articles, verify cache."""
        # Insert 5 articles with recent dates
        for i in range(5):
            db.upsert_article(
                f"dig-{i}",
                "TechFeed",
                f"Tech Article {i}",
                f"https://x.com/{i}",
                f"Description {i}",
                datetime.now(),
            )

        provider = _mock_provider("## Key Themes\n- AI is everywhere\n## Top Highlights\n...")
        config = DigestConfig(enabled=True, period_days=7, max_articles=20)

        content, count = get_or_generate_digest(db, provider, config)
        assert "Key Themes" in content
        assert count == 5
        provider.generate.assert_called_once()

        # Second call should hit cache (less than 1 day old)
        content2, count2 = get_or_generate_digest(db, provider, config)
        assert content2 == content
        assert count2 == count
        # Provider should NOT be called again
        assert provider.generate.call_count == 1

    def test_digest_no_articles_raises(self, db: Database) -> None:
        """Digest with no articles raises ValueError."""
        provider = _mock_provider()
        config = DigestConfig(enabled=True, period_days=7)

        with pytest.raises(ValueError):
            get_or_generate_digest(db, provider, config)

    def test_digest_to_obsidian(self, obsidian_config: ObsidianConfig) -> None:
        """Save digest to Obsidian and verify file structure."""
        content = "## Key Themes\n- AI advances\n## Top Highlights\n- Article 1"
        filepath = save_digest_note(content, 5, obsidian_config, period_days=7)

        assert filepath.exists()
        text = filepath.read_text(encoding="utf-8")
        assert "Weekly Digest" in text
        assert "article_count: 5" in text
        assert "Key Themes" in text
        assert "digest" in text  # tag

    def test_digest_bookmarked_only(self, db: Database) -> None:
        """Digest with bookmarked_only should only use bookmarked articles."""
        # Insert 3 articles, bookmark 2
        for i in range(3):
            db.upsert_article(
                f"dbm-{i}", "Feed", f"Title {i}", f"https://x.com/{i}", "desc", datetime.now()
            )
        db.toggle_bookmark("dbm-0")
        db.toggle_bookmark("dbm-1")

        provider = _mock_provider("Bookmarked digest")
        config = DigestConfig(enabled=True, period_days=7, bookmarked_only=True)

        content, count = get_or_generate_digest(db, provider, config)
        assert content == "Bookmarked digest"
        assert count == 2


class TestConfigBootstrapFlow:
    """Config load → ensure_dirs → directory creation."""

    def test_ensure_dirs_creates_directories(self, tmp_path: Path) -> None:
        """ensure_dirs creates required directories with correct permissions."""
        config = Config(
            db_path=tmp_path / "data" / "test.db",
            bookmark_dir=tmp_path / "bookmarks",
        )
        ensure_dirs(config)

        assert (tmp_path / "data").is_dir()
        assert (tmp_path / "bookmarks").is_dir()

        # Check permissions (owner-only)
        mode = (tmp_path / "data").stat().st_mode
        assert mode & 0o777 == 0o700

    def test_config_with_obsidian_dirs(self, tmp_path: Path) -> None:
        """ensure_dirs also creates Obsidian vault folder."""
        vault = tmp_path / "vault"
        vault.mkdir()
        config = Config(
            db_path=tmp_path / "data" / "test.db",
            bookmark_dir=tmp_path / "bookmarks",
            obsidian=ObsidianConfig(
                enabled=True,
                vault_path=vault,
                folder="hd-notes",
            ),
        )
        ensure_dirs(config)
        assert (vault / "hd-notes").is_dir()

    def test_load_config_missing_file_defaults(self, tmp_path: Path) -> None:
        """Loading config from non-existent path uses defaults."""
        config = load_config(tmp_path / "nonexistent.yml")
        assert config.language == "en"
        assert config.theme == "textual-dark"
        assert config.digest.enabled is True
        assert config.digest.period_days == 7


class TestDigestThreadSafety:
    """Digest generation from worker thread → main thread read."""

    def test_save_digest_from_thread(self, db: Database) -> None:
        """Save digest from a background thread, read from main thread."""
        # Insert articles
        for i in range(3):
            db.upsert_article(
                f"ts-{i}", "Feed", f"Title {i}", f"https://x.com/{i}", "desc", datetime.now()
            )

        result_holder: dict = {}

        def worker():
            content = "Thread-generated digest content"
            digest_id = db.save_digest(7, 3, content)
            result_holder["id"] = digest_id

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()

        # Read from main thread
        assert "id" in result_holder
        digest = db.get_latest_digest(7)
        assert digest is not None
        assert digest.content == "Thread-generated digest content"
        assert digest.article_count == 3

    def test_concurrent_digest_operations(self, db: Database) -> None:
        """Multiple threads saving digests concurrently."""
        errors: list[Exception] = []

        def worker(period: int):
            try:
                db.save_digest(period, 5, f"Digest for {period} days")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(1, 6)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors in threads: {errors}"


class TestDigestObsidianSaveMethod:
    """Test _save_digest_to_obsidian uses notify (not StatusBar query)."""

    def test_save_success_notifies(self, obsidian_config: ObsidianConfig) -> None:
        """Successful Obsidian save calls notify, not query_one(StatusBar)."""
        from hawaiidisco.app import HawaiiDiscoApp

        fake_self = MagicMock(spec=HawaiiDiscoApp)
        fake_self.config = MagicMock()
        fake_self.config.obsidian = obsidian_config
        fake_self.config.digest.period_days = 7

        content = "## Themes\n- AI"
        HawaiiDiscoApp._save_digest_to_obsidian(fake_self, content, 3)

        fake_self.notify.assert_called_once()
        assert "obsidian" in fake_self.notify.call_args[0][0].lower() or "저장" in fake_self.notify.call_args[0][0]
        # Must NOT touch query_one
        fake_self.query_one.assert_not_called()

    def test_disabled_obsidian_notifies(self) -> None:
        """Disabled Obsidian config calls notify with warning."""
        from hawaiidisco.app import HawaiiDiscoApp

        fake_self = MagicMock(spec=HawaiiDiscoApp)
        fake_self.config = MagicMock()
        fake_self.config.obsidian = ObsidianConfig(enabled=False)

        HawaiiDiscoApp._save_digest_to_obsidian(fake_self, "content", 1)

        fake_self.notify.assert_called_once()
        assert fake_self.notify.call_args[1].get("severity") == "warning"
        fake_self.query_one.assert_not_called()

    def test_invalid_vault_notifies(self, tmp_path: Path) -> None:
        """Invalid vault path calls notify with error."""
        from hawaiidisco.app import HawaiiDiscoApp

        fake_self = MagicMock(spec=HawaiiDiscoApp)
        fake_self.config = MagicMock()
        fake_self.config.obsidian = ObsidianConfig(
            enabled=True,
            vault_path=tmp_path / "nonexistent",
            folder="notes",
        )

        HawaiiDiscoApp._save_digest_to_obsidian(fake_self, "content", 1)

        fake_self.notify.assert_called_once()
        assert fake_self.notify.call_args[1].get("severity") == "error"
        fake_self.query_one.assert_not_called()
