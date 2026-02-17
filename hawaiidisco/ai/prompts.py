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


# 인사이트 생성 프롬프트 (persona 미설정 시 기본값 — 범용)
INSIGHT_PROMPT: str = (
    "You are an intelligent reader analyzing an article. "
    "Based on the title and description below, provide a sharp, opinionated insight in 1-2 sentences. "
    "Focus on WHY this matters: its practical impact, hidden implications, or what readers should watch out for. "
    "Do NOT simply restate the title or summarize. Instead, add your own analytical perspective. "
    "Keep technical terms as-is. "
    "Respond in {output_language}.\n\n"
    "<article>\n"
    "<title>{title}</title>\n"
    "<description>{description}</description>\n"
    "</article>"
)

# 사용자 맞춤 인사이트 프롬프트 (persona 설정 시)
INSIGHT_PROMPT_PERSONA: str = (
    "You are an intelligent reader providing personalized insights.\n\n"
    "<reader_profile>\n{persona}\n</reader_profile>\n\n"
    "Based on the reader's background, analyze the article below and provide a sharp, "
    "relevant insight in 1-2 sentences. Focus on what specifically matters to THIS reader: "
    "practical implications for their role, opportunities they should notice, risks to watch out for, "
    "or connections to their domain.\n"
    "Do NOT simply restate the title or summarize. Add analytical perspective tailored to the reader's context. "
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

# 제목/설명 파싱 키 (항상 영어)
TRANSLATE_META_KEYS: tuple[str, str] = ("Title:", "Description:")

# 북마크 분석 프롬프트 (persona 미설정 시 기본값)
BOOKMARK_ANALYSIS_PROMPT: str = (
    "Below are articles I bookmarked.\n\n"
    "<bookmarks>\n{bookmarks}\n</bookmarks>\n\n"
    "Please analyze the following and respond in {output_language}:\n"
    "1. Common themes and topics across these bookmarks\n"
    "2. Key insights and takeaways\n"
    "3. Suggested areas to explore further"
)

# 북마크 분석 프롬프트 (persona 설정 시)
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

# 북마크 분석 항목 템플릿
BOOKMARK_ANALYSIS_ITEM: str = (
    "- Title: {title}\n  Description: {description}\n  Insight: {insight}"
)

# 설명 없음 플레이스홀더
NONE_TEXT: str = "(none)"
