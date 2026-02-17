"""AI-powered article digest generation."""
from __future__ import annotations

from datetime import datetime, timedelta

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.ai.prompts import (
    DIGEST_ARTICLE_ITEM,
    DIGEST_PROMPT,
    NONE_TEXT,
    get_lang_name,
)
from hawaiidisco.config import DigestConfig
from hawaiidisco.db import Article, Database
from hawaiidisco.i18n import get_lang, t


def generate_digest(
    articles: list[Article],
    provider: AIProvider,
    period_days: int = 7,
    lang: str = "",
) -> str | None:
    """Generate a digest using the AI provider. Return None on failure."""
    if not provider.is_available():
        return None

    lang = lang or get_lang().value

    articles_text = "\n".join(
        DIGEST_ARTICLE_ITEM.format(
            title=a.title,
            feed_name=a.feed_name,
            date=(a.published_at or a.fetched_at).strftime("%Y-%m-%d"),
            description=a.description or NONE_TEXT,
            insight=a.insight or NONE_TEXT,
        )
        for a in articles
    )

    prompt = DIGEST_PROMPT.format(
        output_language=get_lang_name(lang),
        period_days=period_days,
        articles=articles_text,
    )

    return provider.generate(prompt, timeout=90)


def get_or_generate_digest(
    db: Database,
    provider: AIProvider,
    config: DigestConfig,
) -> tuple[str, int]:
    """Return a cached digest if fresh, otherwise generate and save a new one.

    Returns (content, article_count). Raises ValueError if no articles found.
    """
    # Check for a fresh cached digest (less than 1 day old)
    cached = db.get_latest_digest(config.period_days)
    if cached:
        age = datetime.now() - cached.created_at
        if age < timedelta(days=1):
            return cached.content, cached.article_count

    # Fetch recent articles
    if config.bookmarked_only:
        articles = db.get_recent_bookmarked_articles(config.period_days)
        articles = articles[: config.max_articles]
    else:
        articles = db.get_recent_articles(config.period_days, config.max_articles)

    if not articles:
        raise ValueError(t("no_recent_articles_for_digest"))

    content = generate_digest(articles, provider, config.period_days)
    if not content:
        raise ValueError(t("digest_generation_failed"))

    # Save to DB
    db.save_digest(config.period_days, len(articles), content)

    return content, len(articles)
