"""AI-powered translation."""
from __future__ import annotations

import logging

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.ai.prompts import (
    TRANSLATE_BODY_PROMPT,
    TRANSLATE_META_PROMPT,
    TRANSLATE_META_KEYS,
    TRANSLATABLE_LANGS,
    NONE_TEXT,
    get_lang_name,
)
from hawaiidisco.i18n import get_lang, t

logger = logging.getLogger(__name__)


def translate_text(text: str, provider: AIProvider, *, timeout: int = 60, lang: str = "") -> str | None:
    """Translate text using the AI provider."""
    if not provider.is_available() or not text:
        return None

    lang = lang or get_lang().value
    if lang == "en" or lang not in TRANSLATABLE_LANGS:
        return None

    # Limit long text to 10,000 characters
    truncated = text[:10000]
    prompt = TRANSLATE_BODY_PROMPT.format(
        output_language=get_lang_name(lang),
        text=truncated,
    )

    return provider.generate(prompt, timeout=timeout)


def translate_article_meta(
    title: str,
    description: str | None,
    provider: AIProvider,
    lang: str = "",
) -> tuple[str, str]:
    """Translate title and description together. Return (translated_title, translated_desc)."""
    if not provider.is_available():
        return t("claude_cli_not_found"), ""

    lang = lang or get_lang().value
    if lang == "en" or lang not in TRANSLATABLE_LANGS:
        return "", ""

    desc_part = description or NONE_TEXT

    prompt = TRANSLATE_META_PROMPT.format(
        output_language=get_lang_name(lang),
        title=title,
        description=desc_part,
    )

    try:
        result = provider.generate(prompt, timeout=30)
        if result:
            return _parse_translation(result, title)
    except Exception:
        logger.debug("번역 실패", exc_info=True)

    return t("translation_failed_short"), ""


def _parse_translation(output: str, fallback_title: str) -> tuple[str, str]:
    """Parse title and description from AI output."""
    title_key, desc_key = TRANSLATE_META_KEYS

    translated_title = ""
    translated_desc = ""

    for line in output.split("\n"):
        line = line.strip()
        if line.startswith(title_key):
            translated_title = line[len(title_key):].strip()
        elif line.startswith(desc_key):
            translated_desc = line[len(desc_key):].strip()

    # On parse failure, use the first line as title; fall back to original if empty
    if not translated_title:
        first_line = output.split("\n")[0].strip()
        # 첫 줄이 키 자체이거나 비어있으면 fallback 사용
        if not first_line or first_line == title_key.strip() or first_line == title_key.rstrip(":"):
            translated_title = fallback_title
        else:
            translated_title = first_line

    return translated_title, translated_desc
