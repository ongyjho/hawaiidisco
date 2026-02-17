"""AI prompt templates (English base + dynamic output language injection)."""
from __future__ import annotations

# Language code to language name mapping
LANG_NAMES: dict[str, str] = {
    "en": "English",
    "ko": "Korean",
    "ja": "Japanese",
    "zh-CN": "Simplified Chinese",
    "es": "Spanish",
    "de": "German",
}

# Translatable languages (excluding English)
TRANSLATABLE_LANGS: frozenset[str] = frozenset({"ko", "ja", "zh-CN", "es", "de"})


def get_lang_name(lang: str) -> str:
    """Convert a language code to its display name."""
    return LANG_NAMES.get(lang, lang)


# Insight prompt (default, generic — used when persona is not set)
INSIGHT_PROMPT: str = (
    "You are an intelligent reader analyzing an article. "
    "First, identify the article's domain (technology, politics, business, economics, science, culture, sports, etc.). "
    "Then provide a sharp, opinionated insight in 1-2 sentences from the appropriate perspective for that domain. "
    "For example, analyze political articles from a political/policy perspective, "
    "business articles from a market/strategy perspective, and so on. "
    "Do NOT analyze non-tech articles from a technical perspective. "
    "Focus on WHY this matters: its practical impact, hidden implications, or what readers should watch out for. "
    "Do NOT simply restate the title or summarize. Instead, add your own analytical perspective. "
    "Keep technical terms as-is. "
    "Respond in {output_language}.\n\n"
    "<article>\n"
    "<title>{title}</title>\n"
    "<description>{description}</description>\n"
    "</article>"
)

# Personalized insight prompt (used when persona is set)
INSIGHT_PROMPT_PERSONA: str = (
    "You are an intelligent reader providing personalized insights.\n\n"
    "<reader_profile>\n{persona}\n</reader_profile>\n\n"
    "First, identify the article's domain (technology, politics, business, economics, science, culture, sports, etc.). "
    "Then analyze the article from the appropriate perspective for that domain.\n"
    "If the article is within the reader's primary domain, provide a sharp insight tailored to their role. "
    "If the article is outside the reader's primary domain (e.g., a political article for a tech reader), "
    "analyze it from the article's own domain perspective first, "
    "then briefly note any relevance to the reader's context if applicable.\n"
    "Do NOT force a technical analysis on non-tech articles. "
    "Provide a sharp, relevant insight in 1-2 sentences. "
    "Do NOT simply restate the title or summarize. Add analytical perspective. "
    "Keep technical terms as-is. "
    "Respond in {output_language}.\n\n"
    "<article>\n"
    "<title>{title}</title>\n"
    "<description>{description}</description>\n"
    "</article>"
)

# Body translation prompt
TRANSLATE_BODY_PROMPT: str = (
    "Translate the English text below into natural {output_language}. "
    "For technical terms, include the English in parentheses "
    "(e.g., Container(Container)). "
    "Output only the translation without any other explanation.\n\n"
    "<text>\n{text}\n</text>"
)

# Title + description translation prompt
TRANSLATE_META_PROMPT: str = (
    "Translate the title and description of the English article below "
    "into natural {output_language}. "
    "For technical terms, include the English in parentheses "
    "(e.g., Container(Container)). "
    "Output only in the following format:\n"
    "Title: (translated title)\n"
    "Description: (translated description)\n\n"
    "<article>\n"
    "<title>{title}</title>\n"
    "<description>{description}</description>\n"
    "</article>"
)

# Title/description parsing keys (always English)
TRANSLATE_META_KEYS: tuple[str, str] = ("Title:", "Description:")

# Bookmark analysis prompt (default, used when persona is not set)
BOOKMARK_ANALYSIS_PROMPT: str = (
    "Below are articles I bookmarked.\n\n"
    "<bookmarks>\n{bookmarks}\n</bookmarks>\n\n"
    "Please analyze the following and respond in {output_language}:\n"
    "1. Common themes and topics across these bookmarks\n"
    "2. Key insights and takeaways\n"
    "3. Suggested areas to explore further"
)

# Bookmark analysis prompt (used when persona is set)
BOOKMARK_ANALYSIS_PROMPT_PERSONA: str = (
    "Below are articles I bookmarked.\n\n"
    "<reader_profile>\n{persona}\n</reader_profile>\n\n"
    "<bookmarks>\n{bookmarks}\n</bookmarks>\n\n"
    "Based on the reader's background and interests, analyze the following "
    "and respond in {output_language}:\n"
    "1. Common themes and topics across these bookmarks\n"
    "2. Key insights and takeaways — highlight what is most relevant to THIS reader\n"
    "3. Suggested areas to explore further, tailored to their role and goals"
)

# Bookmark analysis item template
BOOKMARK_ANALYSIS_ITEM: str = (
    "- Title: {title}\n  Description: {description}\n  Insight: {insight}"
)

# 다이제스트 프롬프트
DIGEST_PROMPT: str = (
    "You are a senior editor creating a weekly digest of notable articles.\n"
    "Below are the articles from the past {period_days} days.\n\n"
    "<articles>\n{articles}\n</articles>\n\n"
    "Please create a concise, well-structured digest in {output_language}:\n"
    "1. **Key Themes**: Identify 2-4 major themes or trends across these articles\n"
    "2. **Top Highlights**: Summarize the 3-5 most important articles with why they matter\n"
    "3. **What to Watch**: Briefly note emerging topics or implications worth noting\n\n"
    "Analyze each article from its own domain perspective (tech, politics, business, etc.). "
    "Keep the digest focused and actionable. Use markdown formatting."
)

# 다이제스트 아티클 항목 템플릿
DIGEST_ARTICLE_ITEM: str = (
    "- Title: {title}\n  Feed: {feed_name}\n  Date: {date}\n"
    "  Description: {description}\n  Insight: {insight}"
)

# No-description placeholder
NONE_TEXT: str = "(none)"
