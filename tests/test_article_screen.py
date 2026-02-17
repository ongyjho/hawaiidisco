"""Tests for ArticleScreen initialization and pre-mount call safety."""
from __future__ import annotations

from hawaiidisco.screens import ArticleScreen


class TestArticleScreenInit:
    """Tests for ArticleScreen initialization parameters."""

    def test_default_init(self) -> None:
        """Create with default parameters."""
        screen = ArticleScreen(
            title="Test",
            meta="TestFeed | 2025-01-01",
            body="loading...",
            link="https://example.com",
        )
        assert screen._article_id is None
        assert screen._translated_body is None
        assert screen._description is None
        assert screen._insight is None

    def test_init_with_article_id(self) -> None:
        """Create with an article_id."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
            article_id="art-123",
        )
        assert screen._article_id == "art-123"

    def test_init_with_translated_body(self) -> None:
        """Create with a cached translated_body."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
            article_id="art-123",
            translated_body="번역된 본문",
        )
        assert screen._translated_body == "번역된 본문"


class TestUpdateBodyBeforeMount:
    """Calling update_body before widget mount should not raise NoMatches."""

    def test_update_body_before_mount_no_crash(self) -> None:
        """Calling update_body before mount works without exceptions."""
        screen = ArticleScreen(
            title="Test",
            meta="TestFeed | 2025-01-01",
            body="loading...",
            link="https://example.com",
        )
        screen.update_body("에러 메시지: SSL EOF")
        assert screen._body == "에러 메시지: SSL EOF"

    def test_update_body_stores_value_for_compose(self) -> None:
        """Value stored via update_body is used during compose."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="initial",
            link="https://example.com",
        )
        screen.update_body("updated body")
        assert screen._body == "updated body"


class TestUpdateTranslatedBodyBeforeMount:
    """Tests for update_translated_body call safety before widget mount."""

    def test_update_translated_body_before_mount_no_crash(self) -> None:
        """Calling update_translated_body before mount works without exceptions."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
        )
        screen.update_translated_body("번역된 텍스트")
        assert screen._translated_body == "번역된 텍스트"

    def test_update_translated_body_stores_value(self) -> None:
        """Value stored via update_translated_body is reflected in internal state."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
            article_id="art-1",
        )
        screen.update_translated_body("새 번역")
        assert screen._translated_body == "새 번역"


class TestArticleScreenInsight:
    """Tests for ArticleScreen insight functionality."""

    def test_init_with_insight(self) -> None:
        """Create with an insight parameter."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
            article_id="art-1",
            insight="핵심 인사이트 내용",
        )
        assert screen._insight == "핵심 인사이트 내용"

    def test_init_with_description(self) -> None:
        """Create with a description parameter."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
            description="글 요약 내용",
        )
        assert screen._description == "글 요약 내용"

    def test_init_defaults_none(self) -> None:
        """Default values for description and insight are None."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
        )
        assert screen._description is None
        assert screen._insight is None

    def test_update_insight_before_mount_no_crash(self) -> None:
        """Calling update_insight before mount works without exceptions."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
        )
        screen.update_insight("새 인사이트")
        assert screen._insight == "새 인사이트"

    def test_update_insight_stores_value(self) -> None:
        """Value stored via update_insight is reflected in internal state."""
        screen = ArticleScreen(
            title="Test",
            meta="meta",
            body="body",
            link="https://example.com",
            article_id="art-1",
        )
        screen.update_insight("업데이트된 인사이트")
        assert screen._insight == "업데이트된 인사이트"
