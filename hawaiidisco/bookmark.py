"""Save bookmarks as Markdown files."""
from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from hawaiidisco.db import Article, Database
from hawaiidisco.i18n import t


def _slugify(text: str, max_len: int = 50) -> str:
    """Convert a title into a filename-safe slug."""
    # Replace whitespace with hyphens
    slug = re.sub(r"\s+", "-", text.strip())
    # Remove characters unsuitable for filenames
    slug = re.sub(r"[^\w가-힣\-]", "", slug)
    return slug[:max_len]


def _safe_path(bookmark_dir: Path, filename: str) -> Path:
    """경로가 bookmark_dir 하위인지 검증한다."""
    filepath = (bookmark_dir / filename).resolve()
    if not filepath.is_relative_to(bookmark_dir.resolve()):
        raise ValueError(f"Path traversal detected: {filename}")
    return filepath


def save_bookmark_md(article: Article, bookmark_dir: Path, memo: str | None = None) -> Path:
    """Save a bookmark as a Markdown file. Return the created file path."""
    bookmark_dir.mkdir(parents=True, exist_ok=True)

    date_str = ""
    if article.published_at:
        date_str = article.published_at.strftime("%Y-%m-%d")
    else:
        date_str = article.fetched_at.strftime("%Y-%m-%d")

    slug = _slugify(article.title)
    filename = f"{date_str}-{slug}.md"
    filepath = _safe_path(bookmark_dir, filename)

    lines = [
        f"# {article.title}",
        "",
        f"- **{t('bm_source')}**: {article.feed_name}",
        f"- **{t('bm_date')}**: {date_str}",
        f"- **{t('bm_link')}**: {article.link}",
    ]

    if article.insight:
        lines.append(f"- **{t('bm_insight')}**: {article.insight}")

    lines.append("")
    lines.append(t("bm_memo_section"))
    lines.append(memo or t("bm_no_memo"))
    lines.append("")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    return filepath


def delete_bookmark_md(article: Article, bookmark_dir: Path) -> None:
    """Delete a bookmark Markdown file."""
    date_str = ""
    if article.published_at:
        date_str = article.published_at.strftime("%Y-%m-%d")
    else:
        date_str = article.fetched_at.strftime("%Y-%m-%d")

    slug = _slugify(article.title)
    filename = f"{date_str}-{slug}.md"
    filepath = _safe_path(bookmark_dir, filename)

    if filepath.exists():
        filepath.unlink()
