"""Save bookmarks as Markdown files."""
from __future__ import annotations

from pathlib import Path

from hawaiidisco.db import Article
from hawaiidisco.i18n import t
from hawaiidisco.md_render import article_date_str, safe_path, slugify

# Backward-compatible aliases for external callers and tests
_slugify = slugify
_safe_path = safe_path


def save_bookmark_md(article: Article, bookmark_dir: Path, memo: str | None = None) -> Path:
    """Save a bookmark as a Markdown file. Return the created file path."""
    bookmark_dir.mkdir(parents=True, exist_ok=True)

    date_str = article_date_str(article)
    slug = slugify(article.title)
    filename = f"{date_str}-{slug}.md"
    filepath = safe_path(bookmark_dir, filename)

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
    date_str = article_date_str(article)
    slug = slugify(article.title)
    filename = f"{date_str}-{slug}.md"
    filepath = safe_path(bookmark_dir, filename)

    if filepath.exists():
        filepath.unlink()
