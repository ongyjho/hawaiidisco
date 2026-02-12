"""AI insight generation."""
from __future__ import annotations

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.ai.prompts import INSIGHT_PROMPT, NONE_TEXT, get_lang_name
from hawaiidisco.db import Article, Database
from hawaiidisco.i18n import get_lang, t


def generate_insight(article: Article, provider: AIProvider, lang: str = "") -> str | None:
    """Generate an insight using the AI provider. Return None on failure."""
    if not provider.is_available():
        return None

    lang = lang or get_lang().value

    prompt = INSIGHT_PROMPT.format(
        output_language=get_lang_name(lang),
        title=article.title,
        description=article.description or NONE_TEXT,
    )

    return provider.generate(prompt, timeout=30)


def get_or_generate_insight(article: Article, db: Database, provider: AIProvider) -> str:
    """Return a cached insight if available; otherwise generate and save one."""
    if article.insight:
        return article.insight

    if not provider.is_available():
        return t("claude_cli_not_found")

    insight = generate_insight(article, provider)
    if insight:
        db.set_insight(article.id, insight)
        return insight

    return t("insight_failed")
