"""Obsidian vault integration -- save articles as Obsidian-formatted notes."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from hawaiidisco.config import ObsidianConfig
from hawaiidisco.db import Article
from hawaiidisco.md_render import article_date_str, feed_subfolder_name, safe_path, slugify


def _escape_yaml(text: str) -> str:
    """Escape characters that could break YAML double-quoted strings."""
    return text.replace("\\", "\\\\").replace('"', '\\"')


def _build_frontmatter(
    article: Article,
    config: ObsidianConfig,
    tags: list[str] | None = None,
) -> str:
    """Build YAML frontmatter block for an Obsidian note."""
    date_str = article_date_str(article)
    prefix = config.tags_prefix

    fm_tags = [prefix]
    feed_tag = f"{prefix}/{feed_subfolder_name(article.feed_name)}"
    fm_tags.append(feed_tag)
    if tags:
        for tag in tags:
            fm_tags.append(f"{prefix}/{tag}")

    lines = [
        "---",
        f'title: "{_escape_yaml(article.title)}"',
        f"source: {article.link}",
        f"feed: {article.feed_name}",
        f"date: {date_str}",
        "tags:",
    ]
    for tag in fm_tags:
        lines.append(f"  - {tag}")
    lines.append("created_by: hawaiidisco")
    lines.append("---")
    return "\n".join(lines)


def _build_body(
    article: Article,
    config: ObsidianConfig,
    memo: str | None = None,
) -> str:
    """Build the Obsidian note body (below frontmatter)."""
    lines: list[str] = []

    lines.append(f"# {article.title}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(article.description or "*(No summary available)*")
    lines.append("")

    # AI Insight (conditional)
    if config.include_insight and article.insight:
        lines.append("## AI Insight")
        lines.append("")
        lines.append(article.insight)
        lines.append("")

    # Translation (conditional)
    if config.include_translation:
        has_translation = article.translated_title or article.translated_desc or article.translated_body
        if has_translation:
            lines.append("## Translation")
            lines.append("")
            if article.translated_title:
                lines.append(f"**Title**: {article.translated_title}")
                lines.append("")
            if article.translated_desc:
                lines.append(f"**Description**: {article.translated_desc}")
                lines.append("")
            if article.translated_body:
                lines.append(article.translated_body)
                lines.append("")

    # My Notes
    lines.append("## My Notes")
    lines.append("")
    lines.append(memo or "*(No notes yet)*")
    lines.append("")

    # Footer
    lines.append("---")
    now_str = datetime.now().strftime("%Y-%m-%d")
    lines.append(f"*Saved from Hawaii Disco on {now_str}*")
    lines.append(f"*Original: [{article.title}]({article.link})*")
    lines.append("")

    return "\n".join(lines)


def _note_path(article: Article, config: ObsidianConfig) -> Path:
    """Compute the full path for an Obsidian note file.

    Structure: vault_path / folder / feed_subfolder / YYYY-MM-DD_slug.md
    """
    base_dir = config.vault_path / config.folder
    feed_dir_name = feed_subfolder_name(article.feed_name)

    date_str = article_date_str(article)
    slug = slugify(article.title)
    filename = f"{date_str}_{slug}.md"

    # Validate path safety against the base dir
    safe_path(base_dir, f"{feed_dir_name}/{filename}")

    return base_dir / feed_dir_name / filename


def _extract_existing_memo(content: str) -> str | None:
    """Extract the My Notes section content from an existing Obsidian note."""
    marker = "## My Notes"
    if marker not in content:
        return None

    idx = content.index(marker) + len(marker)
    rest = content[idx:]

    lines = rest.split("\n")
    memo_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped == "---" or (stripped.startswith("## ") and memo_lines):
            break
        memo_lines.append(line)

    memo_text = "\n".join(memo_lines).strip()
    if memo_text == "*(No notes yet)*":
        return None
    return memo_text or None


def save_obsidian_note(
    article: Article,
    config: ObsidianConfig,
    memo: str | None = None,
    tags: list[str] | None = None,
) -> Path:
    """Save an article as an Obsidian-formatted note. Returns the file path.

    If the file already exists, it updates the note by merging new content
    (insight, translation, memo) without overwriting existing user memo.
    """
    filepath = _note_path(article, config)
    filepath.parent.mkdir(parents=True, exist_ok=True)

    if filepath.exists():
        return _update_obsidian_note(filepath, article, config, memo, tags)

    frontmatter = _build_frontmatter(article, config, tags)
    body = _build_body(article, config, memo)
    content = frontmatter + "\n\n" + body
    filepath.write_text(content, encoding="utf-8")
    return filepath


def _update_obsidian_note(
    filepath: Path,
    article: Article,
    config: ObsidianConfig,
    memo: str | None = None,
    tags: list[str] | None = None,
) -> Path:
    """Update an existing Obsidian note, preserving user memo if no new memo provided."""
    existing_content = filepath.read_text(encoding="utf-8")

    if memo is None:
        memo = _extract_existing_memo(existing_content)

    frontmatter = _build_frontmatter(article, config, tags)
    body = _build_body(article, config, memo)
    content = frontmatter + "\n\n" + body
    filepath.write_text(content, encoding="utf-8")
    return filepath


def delete_obsidian_note(article: Article, config: ObsidianConfig) -> None:
    """Delete an Obsidian note file for the given article, if it exists."""
    filepath = _note_path(article, config)
    if filepath.exists():
        filepath.unlink()


def save_digest_note(
    content: str,
    article_count: int,
    config: ObsidianConfig,
    period_days: int = 7,
) -> Path:
    """Save a digest as an Obsidian-formatted note. Returns the file path."""
    base_dir = config.vault_path / config.folder / "digests"
    base_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    filename = f"{date_str}_weekly_digest.md"
    filepath = base_dir / filename

    prefix = config.tags_prefix
    frontmatter = "\n".join([
        "---",
        f'title: "Weekly Digest {date_str}"',
        f"date: {date_str}",
        f"period_days: {period_days}",
        f"article_count: {article_count}",
        "tags:",
        f"  - {prefix}",
        f"  - {prefix}/digest",
        "created_by: hawaiidisco",
        "---",
    ])

    body_lines = [
        f"# Weekly Digest ({date_str})",
        "",
        f"*{article_count} articles from the past {period_days} days*",
        "",
        content,
        "",
        "---",
        f"*Generated by Hawaii Disco on {date_str}*",
        "",
    ]
    body = "\n".join(body_lines)

    full_content = frontmatter + "\n\n" + body
    filepath.write_text(full_content, encoding="utf-8")
    return filepath


def validate_vault_path(config: ObsidianConfig) -> bool:
    """Check whether the configured vault path exists and is a directory."""
    if not config.enabled:
        return True
    if config.vault_path == Path(""):
        return False
    return config.vault_path.is_dir()
