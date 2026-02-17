"""AI 프롬프트 템플릿 (단일 영어 + 출력 언어 동적 주입)"""
from __future__ import annotations

# 언어 코드 → 언어명 매핑
LANG_NAMES: dict[str, str] = {
    "en": "English",
    "ko": "Korean",
    "ja": "Japanese",
    "zh-CN": "Simplified Chinese",
    "es": "Spanish",
    "de": "German",
}

# 번역 대상 언어 (영어 제외)
TRANSLATABLE_LANGS: frozenset[str] = frozenset({"ko", "ja", "zh-CN", "es", "de"})


def get_lang_name(lang: str) -> str:
    """언어 코드를 언어명으로 변환한다."""
    return LANG_NAMES.get(lang, lang)


# 인사이트 생성 프롬프트
INSIGHT_PROMPT: str = (
    "You are a senior engineer reviewing a tech article. "
    "Based on the title and description below, provide a sharp, opinionated insight in 1-2 sentences. "
    "Focus on WHY this matters: its practical impact, hidden implications, or what engineers should watch out for. "
    "Do NOT simply restate the title or summarize. Instead, add your own analytical perspective. "
    "Keep technical terms as-is. "
    "Respond in {output_language}.\n\n"
    "<article>\n"
    "<title>{title}</title>\n"
    "<description>{description}</description>\n"
    "</article>"
)

# 본문 번역 프롬프트
TRANSLATE_BODY_PROMPT: str = (
    "Translate the English text below into natural {output_language}. "
    "For technical terms, include the English in parentheses "
    "(e.g., Container(Container)). "
    "Output only the translation without any other explanation.\n\n"
    "<text>\n{text}\n</text>"
)

# 제목+설명 번역 프롬프트
TRANSLATE_META_PROMPT: str = (
    "Translate the title and description of the English tech article below "
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

# 제목/설명 파싱 키 (항상 영어)
TRANSLATE_META_KEYS: tuple[str, str] = ("Title:", "Description:")

# 북마크 분석 프롬프트
BOOKMARK_ANALYSIS_PROMPT: str = (
    "Below are the tech articles I bookmarked.\n\n"
    "<bookmarks>\n{bookmarks}\n</bookmarks>\n\n"
    "Please analyze the following and respond in {output_language}:\n"
    "1. Common themes and topics across these bookmarks\n"
    "2. Key insights and takeaways\n"
    "3. Suggested areas to explore further"
)

# 북마크 분석 항목 템플릿
BOOKMARK_ANALYSIS_ITEM: str = (
    "- Title: {title}\n  Description: {description}\n  Insight: {insight}"
)

# 설명 없음 플레이스홀더
NONE_TEXT: str = "(none)"
