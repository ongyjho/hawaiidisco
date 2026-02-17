"""Shared Markdown rendering utilities for bookmark and Obsidian export."""
from __future__ import annotations

import re
from pathlib import Path

from hawaiidisco.db import Article


def slugify(text: str, max_len: int = 50) -> str:
    """Convert a title into a filename-safe slug. Preserves Korean characters."""
    slug = re.sub(r"\s+", "-", text.strip())
    slug = re.sub(r"[^\w가-힣\-]", "", slug)
    return slug[:max_len]


def safe_path(base_dir: Path, filename: str) -> Path:
    """Verify that the path is under base_dir."""
    filepath = (base_dir / filename).resolve()
    if not filepath.is_relative_to(base_dir.resolve()):
        raise ValueError(f"Path traversal detected: {filename}")
    return filepath


def article_date_str(article: Article) -> str:
    """Return the article's date as YYYY-MM-DD string."""
    if article.published_at:
        return article.published_at.strftime("%Y-%m-%d")
    return article.fetched_at.strftime("%Y-%m-%d")


def feed_subfolder_name(feed_name: str) -> str:
    """Sanitize a feed name for use as a directory name."""
    name = re.sub(r"\s+", "-", feed_name.strip())
    name = re.sub(r"[^\w가-힣\-]", "", name)
    return name or "unknown"
