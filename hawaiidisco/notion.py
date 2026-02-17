"""Notion integration -- save articles and digests to Notion via API."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime

from hawaiidisco.config import NotionConfig
from hawaiidisco.db import Article
from hawaiidisco.md_render import article_date_str

_NOTION_API = "https://api.notion.com"
_NOTION_VERSION = "2022-06-28"
_TEXT_LIMIT = 2000  # Notion rich_text content limit per chunk


# ---------------------------------------------------------------------------
# Low-level API helpers
# ---------------------------------------------------------------------------


def _notion_request(
    endpoint: str,
    payload: dict,
    api_key: str,
    *,
    method: str = "POST",
) -> dict:
    """Make an authenticated request to the Notion API. Returns parsed JSON."""
    url = f"{_NOTION_API}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": _NOTION_VERSION,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _notion_get(endpoint: str, api_key: str) -> dict:
    """GET request to Notion API."""
    url = f"{_NOTION_API}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": _NOTION_VERSION,
    }
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Rich text / block builders
# ---------------------------------------------------------------------------


def _rich_text(text: str) -> list[dict]:
    """Build a Notion rich_text array, chunking at the API limit."""
    if not text:
        return [{"type": "text", "text": {"content": ""}}]
    chunks = [text[i : i + _TEXT_LIMIT] for i in range(0, len(text), _TEXT_LIMIT)]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]


def _heading_block(text: str, level: int = 2) -> dict:
    """Build a heading block (h1/h2/h3)."""
    key = f"heading_{level}"
    return {"object": "block", "type": key, key: {"rich_text": _rich_text(text)}}


def _paragraph_block(text: str) -> dict:
    """Build a paragraph block."""
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": _rich_text(text)},
    }


def _divider_block() -> dict:
    """Build a divider block."""
    return {"object": "block", "type": "divider", "divider": {}}


# ---------------------------------------------------------------------------
# Article content builders
# ---------------------------------------------------------------------------


def _build_article_blocks(
    article: Article,
    config: NotionConfig,
    memo: str | None = None,
) -> list[dict]:
    """Build Notion block children for an article page."""
    blocks: list[dict] = []

    # Summary
    blocks.append(_heading_block("Summary"))
    blocks.append(_paragraph_block(article.description or "(No summary available)"))

    # AI Insight (conditional)
    if config.include_insight and article.insight:
        blocks.append(_heading_block("AI Insight"))
        blocks.append(_paragraph_block(article.insight))

    # Translation (conditional)
    if config.include_translation:
        has_translation = article.translated_title or article.translated_desc or article.translated_body
        if has_translation:
            blocks.append(_heading_block("Translation"))
            if article.translated_title:
                blocks.append(_paragraph_block(f"Title: {article.translated_title}"))
            if article.translated_desc:
                blocks.append(_paragraph_block(f"Description: {article.translated_desc}"))
            if article.translated_body:
                blocks.append(_paragraph_block(article.translated_body))

    # My Notes
    blocks.append(_heading_block("My Notes"))
    blocks.append(_paragraph_block(memo or "(No notes yet)"))

    # Footer
    blocks.append(_divider_block())
    now_str = datetime.now().strftime("%Y-%m-%d")
    blocks.append(_paragraph_block(f"Saved from Hawaii Disco on {now_str}"))
    blocks.append(_paragraph_block(f"Original: {article.link}"))

    return blocks


def _build_article_db_properties(
    article: Article,
    config: NotionConfig,
    tags: list[str] | None = None,
) -> dict:
    """Build Notion database row properties for an article."""
    date_str = article_date_str(article)
    props: dict = {
        "Name": {"title": _rich_text(article.title)},
        "URL": {"url": article.link},
        "Feed": {"rich_text": _rich_text(article.feed_name)},
        "Date": {"date": {"start": date_str}},
        "Source": {"rich_text": _rich_text("Hawaii Disco")},
    }
    if tags:
        prefix = config.tags_prefix
        tag_values = [{"name": prefix}]
        for tag in tags:
            tag_values.append({"name": f"{prefix}/{tag}"})
        props["Tags"] = {"multi_select": tag_values}
    return props


def _build_article_page_properties(article: Article) -> dict:
    """Build Notion page properties for a standalone page (page mode)."""
    return {"title": _rich_text(article.title)}


# ---------------------------------------------------------------------------
# Digest content builders
# ---------------------------------------------------------------------------


def _build_digest_blocks(
    content: str,
    article_count: int,
    period_days: int,
) -> list[dict]:
    """Build Notion block children for a digest page."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    blocks: list[dict] = []

    blocks.append(_heading_block(f"Weekly Digest ({now_str})", level=1))
    blocks.append(_paragraph_block(f"{article_count} articles from the past {period_days} days"))

    # Split content into paragraphs
    for paragraph in content.split("\n\n"):
        stripped = paragraph.strip()
        if stripped:
            blocks.append(_paragraph_block(stripped))

    blocks.append(_divider_block())
    blocks.append(_paragraph_block(f"Generated by Hawaii Disco on {now_str}"))

    return blocks


def _build_digest_db_properties(
    config: NotionConfig,
    period_days: int,
) -> dict:
    """Build Notion database row properties for a digest."""
    now_str = datetime.now().strftime("%Y-%m-%d")
    title = f"Weekly Digest {now_str}"
    prefix = config.tags_prefix
    return {
        "Name": {"title": _rich_text(title)},
        "Date": {"date": {"start": now_str}},
        "Source": {"rich_text": _rich_text("Hawaii Disco")},
        "Tags": {"multi_select": [
            {"name": prefix},
            {"name": f"{prefix}/digest"},
        ]},
    }


# ---------------------------------------------------------------------------
# Public API: save article
# ---------------------------------------------------------------------------


def save_notion_article(
    article: Article,
    config: NotionConfig,
    memo: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Save an article to Notion. Returns the Notion page ID.

    In database mode: creates a row in the configured database.
    In page mode: creates a child page under the configured parent page.
    """
    blocks = _build_article_blocks(article, config, memo)

    if config.mode == "database" and config.database_id:
        properties = _build_article_db_properties(article, config, tags)
        payload: dict = {
            "parent": {"database_id": config.database_id},
            "properties": properties,
            "children": blocks,
        }
    else:
        properties = _build_article_page_properties(article)
        parent_id = config.parent_page_id or config.database_id
        payload = {
            "parent": {"page_id": parent_id},
            "properties": properties,
            "children": blocks,
        }

    result = _notion_request("/v1/pages", payload, config.api_key)
    return result.get("id", "")


# ---------------------------------------------------------------------------
# Public API: save digest
# ---------------------------------------------------------------------------


def save_notion_digest(
    content: str,
    article_count: int,
    config: NotionConfig,
    period_days: int = 7,
) -> str:
    """Save a digest to Notion. Returns the Notion page ID."""
    blocks = _build_digest_blocks(content, article_count, period_days)

    if config.mode == "database" and config.database_id:
        properties = _build_digest_db_properties(config, period_days)
        payload: dict = {
            "parent": {"database_id": config.database_id},
            "properties": properties,
            "children": blocks,
        }
    else:
        now_str = datetime.now().strftime("%Y-%m-%d")
        title = f"Weekly Digest {now_str}"
        properties = {"title": _rich_text(title)}
        parent_id = config.parent_page_id or config.database_id
        payload = {
            "parent": {"page_id": parent_id},
            "properties": properties,
            "children": blocks,
        }

    result = _notion_request("/v1/pages", payload, config.api_key)
    return result.get("id", "")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_notion_config(config: NotionConfig) -> bool:
    """Check whether the Notion config has the required fields."""
    if not config.enabled:
        return True
    if not config.api_key:
        return False
    return bool(config.database_id or config.parent_page_id)


def check_notion_connection(config: NotionConfig) -> bool:
    """Test Notion API connectivity by fetching the target page/database."""
    try:
        if config.mode == "database" and config.database_id:
            _notion_get(f"/v1/databases/{config.database_id}", config.api_key)
        elif config.parent_page_id:
            _notion_get(f"/v1/pages/{config.parent_page_id}", config.api_key)
        else:
            return False
        return True
    except Exception:
        return False
