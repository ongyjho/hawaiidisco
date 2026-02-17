"""Tests for Notion integration."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch

from hawaiidisco.config import NotionConfig
from hawaiidisco.db import Article
from hawaiidisco.notion import (
    _build_article_blocks,
    _build_article_db_properties,
    _build_article_page_properties,
    _build_digest_blocks,
    _build_digest_db_properties,
    _divider_block,
    _heading_block,
    _paragraph_block,
    _rich_text,
    save_notion_article,
    save_notion_digest,
    check_notion_connection,
    validate_notion_config,
)


def _make_article(**kwargs: object) -> Article:
    defaults: dict = {
        "id": "test-1",
        "feed_name": "HackerNews",
        "title": "Test Article Title",
        "link": "https://example.com/article",
        "description": "A test article description",
        "published_at": datetime(2025, 2, 16),
        "fetched_at": datetime(2025, 2, 16, 12, 0),
        "is_read": False,
        "is_bookmarked": True,
        "insight": None,
        "translated_title": None,
        "translated_desc": None,
        "translated_body": None,
    }
    defaults.update(kwargs)
    return Article(**defaults)


def _make_config(**kwargs: object) -> NotionConfig:
    defaults: dict = {
        "enabled": True,
        "api_key": "ntn_test_key",
        "mode": "database",
        "database_id": "db-123",
        "parent_page_id": "",
        "auto_save": True,
        "include_insight": True,
        "include_translation": True,
        "tags_prefix": "hawaiidisco",
    }
    defaults.update(kwargs)
    return NotionConfig(**defaults)


# --- Rich Text ---


class TestRichText:
    def test_basic_text(self) -> None:
        result = _rich_text("Hello")
        assert len(result) == 1
        assert result[0]["type"] == "text"
        assert result[0]["text"]["content"] == "Hello"

    def test_empty_text(self) -> None:
        result = _rich_text("")
        assert len(result) == 1
        assert result[0]["text"]["content"] == ""

    def test_chunking_at_2000_chars(self) -> None:
        long_text = "a" * 4500
        result = _rich_text(long_text)
        assert len(result) == 3
        assert len(result[0]["text"]["content"]) == 2000
        assert len(result[1]["text"]["content"]) == 2000
        assert len(result[2]["text"]["content"]) == 500


# --- Block Builders ---


class TestBlockBuilders:
    def test_heading_block(self) -> None:
        block = _heading_block("Title", level=2)
        assert block["type"] == "heading_2"
        assert block["heading_2"]["rich_text"][0]["text"]["content"] == "Title"

    def test_heading_block_level_1(self) -> None:
        block = _heading_block("Main", level=1)
        assert block["type"] == "heading_1"

    def test_paragraph_block(self) -> None:
        block = _paragraph_block("Some text")
        assert block["type"] == "paragraph"
        assert block["paragraph"]["rich_text"][0]["text"]["content"] == "Some text"

    def test_divider_block(self) -> None:
        block = _divider_block()
        assert block["type"] == "divider"


# --- Article Blocks ---


class TestBuildArticleBlocks:
    def test_basic_blocks(self) -> None:
        config = _make_config()
        article = _make_article()
        blocks = _build_article_blocks(article, config)
        block_texts = str(blocks)
        assert "Summary" in block_texts
        assert "A test article description" in block_texts
        assert "My Notes" in block_texts
        assert "(No notes yet)" in block_texts

    def test_with_insight(self) -> None:
        config = _make_config()
        article = _make_article(insight="Great insight here")
        blocks = _build_article_blocks(article, config)
        block_texts = str(blocks)
        assert "AI Insight" in block_texts
        assert "Great insight here" in block_texts

    def test_insight_excluded_when_disabled(self) -> None:
        config = _make_config(include_insight=False)
        article = _make_article(insight="Hidden insight")
        blocks = _build_article_blocks(article, config)
        block_texts = str(blocks)
        assert "AI Insight" not in block_texts
        assert "Hidden insight" not in block_texts

    def test_insight_excluded_when_none(self) -> None:
        config = _make_config()
        article = _make_article(insight=None)
        blocks = _build_article_blocks(article, config)
        block_texts = str(blocks)
        assert "AI Insight" not in block_texts

    def test_with_translation(self) -> None:
        config = _make_config()
        article = _make_article(
            translated_title="번역된 제목",
            translated_desc="번역된 설명",
        )
        blocks = _build_article_blocks(article, config)
        block_texts = str(blocks)
        assert "Translation" in block_texts
        assert "번역된 제목" in block_texts
        assert "번역된 설명" in block_texts

    def test_translation_excluded_when_disabled(self) -> None:
        config = _make_config(include_translation=False)
        article = _make_article(translated_title="번역")
        blocks = _build_article_blocks(article, config)
        block_texts = str(blocks)
        assert "Translation" not in block_texts

    def test_with_memo(self) -> None:
        config = _make_config()
        article = _make_article()
        blocks = _build_article_blocks(article, config, memo="My personal note")
        block_texts = str(blocks)
        assert "My personal note" in block_texts

    def test_no_description(self) -> None:
        config = _make_config()
        article = _make_article(description=None)
        blocks = _build_article_blocks(article, config)
        block_texts = str(blocks)
        assert "(No summary available)" in block_texts

    def test_footer_present(self) -> None:
        config = _make_config()
        article = _make_article()
        blocks = _build_article_blocks(article, config)
        block_texts = str(blocks)
        assert "Saved from Hawaii Disco on" in block_texts
        assert article.link in block_texts


# --- Article DB Properties ---


class TestBuildArticleDbProperties:
    def test_basic_properties(self) -> None:
        config = _make_config()
        article = _make_article()
        props = _build_article_db_properties(article, config)
        assert "Name" in props
        assert "URL" in props
        assert "Feed" in props
        assert "Date" in props
        assert "Source" in props
        assert props["URL"]["url"] == "https://example.com/article"

    def test_with_tags(self) -> None:
        config = _make_config()
        article = _make_article()
        props = _build_article_db_properties(article, config, tags=["python", "ai"])
        assert "Tags" in props
        tag_names = [t["name"] for t in props["Tags"]["multi_select"]]
        assert "hawaiidisco" in tag_names
        assert "hawaiidisco/python" in tag_names
        assert "hawaiidisco/ai" in tag_names

    def test_without_tags(self) -> None:
        config = _make_config()
        article = _make_article()
        props = _build_article_db_properties(article, config)
        assert "Tags" not in props


# --- Article Page Properties ---


class TestBuildArticlePageProperties:
    def test_has_title(self) -> None:
        article = _make_article()
        props = _build_article_page_properties(article)
        assert "title" in props
        assert props["title"][0]["text"]["content"] == "Test Article Title"


# --- Save Article ---


class TestSaveNotionArticle:
    @patch("hawaiidisco.notion._notion_request")
    def test_database_mode(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {"id": "page-id-123"}
        config = _make_config(mode="database", database_id="db-123")
        article = _make_article()
        page_id = save_notion_article(article, config)
        assert page_id == "page-id-123"
        call_args = mock_req.call_args
        assert call_args[0][0] == "/v1/pages"
        payload = call_args[0][1]
        assert payload["parent"] == {"database_id": "db-123"}
        assert "Name" in payload["properties"]

    @patch("hawaiidisco.notion._notion_request")
    def test_page_mode(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {"id": "page-id-456"}
        config = _make_config(mode="page", database_id="", parent_page_id="parent-123")
        article = _make_article()
        page_id = save_notion_article(article, config)
        assert page_id == "page-id-456"
        payload = mock_req.call_args[0][1]
        assert payload["parent"] == {"page_id": "parent-123"}
        assert "title" in payload["properties"]

    @patch("hawaiidisco.notion._notion_request")
    def test_with_memo_and_tags(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {"id": "page-id-789"}
        config = _make_config()
        article = _make_article(insight="Some insight")
        save_notion_article(article, config, memo="My memo", tags=["tech"])
        payload = mock_req.call_args[0][1]
        children_text = str(payload["children"])
        assert "My memo" in children_text
        assert "Some insight" in children_text
        tag_names = [t["name"] for t in payload["properties"]["Tags"]["multi_select"]]
        assert "hawaiidisco/tech" in tag_names


# --- Digest Blocks ---


class TestBuildDigestBlocks:
    def test_basic_digest_blocks(self) -> None:
        blocks = _build_digest_blocks("Theme 1\n\nTheme 2", 10, 7)
        block_texts = str(blocks)
        assert "Weekly Digest" in block_texts
        assert "10 articles from the past 7 days" in block_texts
        assert "Theme 1" in block_texts
        assert "Theme 2" in block_texts
        assert "Generated by Hawaii Disco" in block_texts


class TestBuildDigestDbProperties:
    def test_has_required_properties(self) -> None:
        config = _make_config()
        props = _build_digest_db_properties(config, 7)
        assert "Name" in props
        assert "Date" in props
        assert "Tags" in props
        tag_names = [t["name"] for t in props["Tags"]["multi_select"]]
        assert "hawaiidisco" in tag_names
        assert "hawaiidisco/digest" in tag_names


# --- Save Digest ---


class TestSaveNotionDigest:
    @patch("hawaiidisco.notion._notion_request")
    def test_database_mode(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {"id": "digest-page-1"}
        config = _make_config(mode="database", database_id="db-123")
        page_id = save_notion_digest("Content here", 15, config, period_days=7)
        assert page_id == "digest-page-1"
        payload = mock_req.call_args[0][1]
        assert payload["parent"] == {"database_id": "db-123"}

    @patch("hawaiidisco.notion._notion_request")
    def test_page_mode(self, mock_req: MagicMock) -> None:
        mock_req.return_value = {"id": "digest-page-2"}
        config = _make_config(mode="page", database_id="", parent_page_id="parent-456")
        page_id = save_notion_digest("Content", 5, config)
        assert page_id == "digest-page-2"
        payload = mock_req.call_args[0][1]
        assert payload["parent"] == {"page_id": "parent-456"}


# --- Validate Config ---


class TestValidateNotionConfig:
    def test_disabled_always_valid(self) -> None:
        config = _make_config(enabled=False, api_key="", database_id="")
        assert validate_notion_config(config) is True

    def test_missing_api_key(self) -> None:
        config = _make_config(enabled=True, api_key="")
        assert validate_notion_config(config) is False

    def test_missing_target(self) -> None:
        config = _make_config(enabled=True, api_key="key", database_id="", parent_page_id="")
        assert validate_notion_config(config) is False

    def test_valid_database_mode(self) -> None:
        config = _make_config(enabled=True, api_key="key", database_id="db-1")
        assert validate_notion_config(config) is True

    def test_valid_page_mode(self) -> None:
        config = _make_config(enabled=True, api_key="key", database_id="", parent_page_id="page-1")
        assert validate_notion_config(config) is True


# --- Test Connection ---


class TestCheckNotionConnection:
    @patch("hawaiidisco.notion._notion_get")
    def test_database_connection_success(self, mock_get: MagicMock) -> None:
        mock_get.return_value = {"id": "db-123"}
        config = _make_config(mode="database", database_id="db-123")
        assert check_notion_connection(config) is True
        mock_get.assert_called_once_with("/v1/databases/db-123", "ntn_test_key")

    @patch("hawaiidisco.notion._notion_get")
    def test_page_connection_success(self, mock_get: MagicMock) -> None:
        mock_get.return_value = {"id": "page-1"}
        config = _make_config(mode="page", database_id="", parent_page_id="page-1")
        assert check_notion_connection(config) is True
        mock_get.assert_called_once_with("/v1/pages/page-1", "ntn_test_key")

    @patch("hawaiidisco.notion._notion_get")
    def test_connection_failure(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = Exception("Network error")
        config = _make_config()
        assert check_notion_connection(config) is False

    def test_no_target(self) -> None:
        config = _make_config(database_id="", parent_page_id="")
        assert check_notion_connection(config) is False
