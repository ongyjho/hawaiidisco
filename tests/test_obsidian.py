"""Tests for Obsidian vault integration."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from hawaiidisco.config import ObsidianConfig
from hawaiidisco.db import Article
from hawaiidisco.obsidian import (
    _build_body,
    _build_frontmatter,
    _extract_existing_memo,
    _note_path,
    delete_obsidian_note,
    save_obsidian_note,
    validate_vault_path,
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


@pytest.fixture()
def obsidian_config(tmp_path: Path) -> ObsidianConfig:
    vault = tmp_path / "vault"
    vault.mkdir()
    return ObsidianConfig(
        enabled=True,
        vault_path=vault,
        folder="hawaii-disco",
        tags_prefix="hawaiidisco",
        include_insight=True,
        include_translation=True,
    )


# --- Frontmatter ---


class TestBuildFrontmatter:
    def test_basic_frontmatter(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        fm = _build_frontmatter(article, obsidian_config)
        assert fm.startswith("---")
        assert fm.endswith("---")
        assert 'title: "Test Article Title"' in fm
        assert "source: https://example.com/article" in fm
        assert "feed: HackerNews" in fm
        assert "date: 2025-02-16" in fm
        assert "  - hawaiidisco" in fm
        assert "  - hawaiidisco/HackerNews" in fm
        assert "created_by: hawaiidisco" in fm

    def test_title_with_quotes_escaped(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article(title='Title with "quotes"')
        fm = _build_frontmatter(article, obsidian_config)
        assert r"\"quotes\"" in fm

    def test_user_tags_included(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        fm = _build_frontmatter(article, obsidian_config, tags=["python", "ai"])
        assert "  - hawaiidisco/python" in fm
        assert "  - hawaiidisco/ai" in fm

    def test_custom_prefix(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        config = ObsidianConfig(enabled=True, vault_path=vault, tags_prefix="hd")
        article = _make_article()
        fm = _build_frontmatter(article, config)
        assert "  - hd" in fm
        assert "  - hd/HackerNews" in fm


# --- Body ---


class TestBuildBody:
    def test_includes_title_and_summary(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        body = _build_body(article, obsidian_config)
        assert "# Test Article Title" in body
        assert "## Summary" in body
        assert "A test article description" in body

    def test_no_description_placeholder(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article(description=None)
        body = _build_body(article, obsidian_config)
        assert "*(No summary available)*" in body

    def test_insight_included_when_present(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article(insight="This is an AI insight")
        body = _build_body(article, obsidian_config)
        assert "## AI Insight" in body
        assert "This is an AI insight" in body

    def test_insight_excluded_when_disabled(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        config = ObsidianConfig(enabled=True, vault_path=vault, include_insight=False)
        article = _make_article(insight="Hidden insight")
        body = _build_body(article, config)
        assert "## AI Insight" not in body

    def test_insight_excluded_when_none(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article(insight=None)
        body = _build_body(article, obsidian_config)
        assert "## AI Insight" not in body

    def test_translation_included(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article(
            translated_title="번역된 제목",
            translated_desc="번역된 설명",
        )
        body = _build_body(article, obsidian_config)
        assert "## Translation" in body
        assert "번역된 제목" in body
        assert "번역된 설명" in body

    def test_translation_excluded_when_disabled(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        config = ObsidianConfig(enabled=True, vault_path=vault, include_translation=False)
        article = _make_article(translated_title="번역")
        body = _build_body(article, config)
        assert "## Translation" not in body

    def test_memo_included(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        body = _build_body(article, obsidian_config, memo="My personal note")
        assert "## My Notes" in body
        assert "My personal note" in body

    def test_default_memo_placeholder(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        body = _build_body(article, obsidian_config)
        assert "*(No notes yet)*" in body

    def test_footer_present(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        body = _build_body(article, obsidian_config)
        assert "Saved from Hawaii Disco on" in body
        assert f"[{article.title}]({article.link})" in body


# --- Note Path ---


class TestNotePath:
    def test_feed_subfolder_structure(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        path = _note_path(article, obsidian_config)
        assert "hawaii-disco" in str(path)
        assert "HackerNews" in str(path)
        assert path.name == "2025-02-16_Test-Article-Title.md"

    def test_path_within_vault(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        path = _note_path(article, obsidian_config)
        assert path.is_relative_to(obsidian_config.vault_path)

    def test_korean_title(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article(title="한국어 제목 테스트")
        path = _note_path(article, obsidian_config)
        assert "한국어-제목-테스트" in path.name


# --- Save / Update / Delete ---


class TestSaveObsidianNote:
    def test_creates_note_file(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        filepath = save_obsidian_note(article, obsidian_config)
        assert filepath.exists()
        content = filepath.read_text(encoding="utf-8")
        assert "---" in content
        assert "# Test Article Title" in content

    def test_creates_feed_subdirectory(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        filepath = save_obsidian_note(article, obsidian_config)
        assert filepath.parent.name == "HackerNews"

    def test_frontmatter_in_content(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        filepath = save_obsidian_note(article, obsidian_config)
        content = filepath.read_text(encoding="utf-8")
        assert content.startswith("---\n")
        assert "created_by: hawaiidisco" in content

    def test_with_all_data(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article(
            insight="Great insight",
            translated_title="번역 제목",
            translated_desc="번역 설명",
        )
        filepath = save_obsidian_note(article, obsidian_config, memo="My memo", tags=["tech"])
        content = filepath.read_text(encoding="utf-8")
        assert "Great insight" in content
        assert "번역 제목" in content
        assert "My memo" in content
        assert "hawaiidisco/tech" in content

    def test_update_existing_note(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        save_obsidian_note(article, obsidian_config, memo="First memo")

        article_with_insight = _make_article(insight="New insight")
        filepath = save_obsidian_note(article_with_insight, obsidian_config, memo="Updated memo")
        content = filepath.read_text(encoding="utf-8")
        assert "New insight" in content
        assert "Updated memo" in content

    def test_preserves_memo_on_update_without_new_memo(
        self, obsidian_config: ObsidianConfig
    ) -> None:
        article = _make_article()
        save_obsidian_note(article, obsidian_config, memo="Original memo")

        article_with_insight = _make_article(insight="New insight")
        filepath = save_obsidian_note(article_with_insight, obsidian_config)
        content = filepath.read_text(encoding="utf-8")
        assert "Original memo" in content
        assert "New insight" in content


class TestDeleteObsidianNote:
    def test_deletes_existing_note(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        filepath = save_obsidian_note(article, obsidian_config)
        assert filepath.exists()
        delete_obsidian_note(article, obsidian_config)
        assert not filepath.exists()

    def test_no_error_when_note_missing(self, obsidian_config: ObsidianConfig) -> None:
        article = _make_article()
        # Should not raise
        delete_obsidian_note(article, obsidian_config)


# --- Validate Vault ---


class TestValidateVaultPath:
    def test_valid_path(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        config = ObsidianConfig(enabled=True, vault_path=vault)
        assert validate_vault_path(config) is True

    def test_missing_path(self) -> None:
        config = ObsidianConfig(enabled=True, vault_path=Path("/nonexistent/vault"))
        assert validate_vault_path(config) is False

    def test_disabled_always_valid(self) -> None:
        config = ObsidianConfig(enabled=False, vault_path=Path(""))
        assert validate_vault_path(config) is True

    def test_empty_path_invalid(self) -> None:
        config = ObsidianConfig(enabled=True, vault_path=Path(""))
        assert validate_vault_path(config) is False


# --- Extract Existing Memo ---


class TestExtractExistingMemo:
    def test_extract_memo(self) -> None:
        content = "## My Notes\n\nExisting user memo\n\n---\n*Saved from*"
        assert _extract_existing_memo(content) == "Existing user memo"

    def test_no_memo_section(self) -> None:
        content = "# Title\n## Summary\nSome text"
        assert _extract_existing_memo(content) is None

    def test_default_placeholder_returns_none(self) -> None:
        content = "## My Notes\n\n*(No notes yet)*\n\n---"
        assert _extract_existing_memo(content) is None

    def test_multiline_memo(self) -> None:
        content = "## My Notes\n\nLine 1\nLine 2\nLine 3\n\n---\n*Saved*"
        result = _extract_existing_memo(content)
        assert result is not None
        assert "Line 1" in result
        assert "Line 2" in result
        assert "Line 3" in result
