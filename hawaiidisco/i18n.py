"""Internationalization (i18n) support."""
from __future__ import annotations

from enum import Enum


class Lang(Enum):
    EN = "en"
    KO = "ko"


_current_lang: Lang = Lang.EN

# {key: {Lang: template_string}}
_STRINGS: dict[str, dict[Lang, str]] = {
    # --- app.py: MemoScreen ---
    "cancel": {Lang.EN: "Cancel", Lang.KO: "취소"},
    "memo_input_help": {
        Lang.EN: "Enter memo (Ctrl+S save, Escape cancel)",
        Lang.KO: "메모 입력 (Ctrl+S 저장, Escape 취소)",
    },
    "close": {Lang.EN: "Close", Lang.KO: "닫기"},
    # --- app.py: ArticleScreen ---
    "browser": {Lang.EN: "Browser", Lang.KO: "브라우저"},
    "translate": {Lang.EN: "Translate", Lang.KO: "번역"},
    "original": {Lang.EN: "Original", Lang.KO: "원문"},
    "loading_body": {
        Lang.EN: "Loading article...",
        Lang.KO: "본문을 불러오는 중...",
    },
    "translation_tab": {Lang.EN: "Translation", Lang.KO: "번역"},
    "press_t_to_translate": {
        Lang.EN: "Press t to translate",
        Lang.KO: "t 키를 눌러 번역하세요",
    },
    "translating": {Lang.EN: "Translating...", Lang.KO: "번역 중..."},
    "insight_tab": {Lang.EN: "Insight", Lang.KO: "인사이트"},
    "press_i_for_insight": {
        Lang.EN: "Press i to generate insight",
        Lang.KO: "i 키를 눌러 인사이트를 생성하세요",
    },
    # --- app.py: AddFeedScreen ---
    "add_feed_help": {
        Lang.EN: "Add feed (Enter next/confirm, Escape cancel)",
        Lang.KO: "피드 추가 (Enter로 다음/확인, Escape 취소)",
    },
    "rss_url_placeholder": {
        Lang.EN: "RSS URL (e.g. https://example.com/feed.xml)",
        Lang.KO: "RSS URL (예: https://example.com/feed.xml)",
    },
    "feed_name_placeholder": {
        Lang.EN: "Feed name (e.g. GeekNews)",
        Lang.KO: "피드 이름 (예: GeekNews)",
    },
    "invalid_url_scheme": {
        Lang.EN: "URL must start with http:// or https://",
        Lang.KO: "URL은 http:// 또는 https://로 시작해야 합니다",
    },
    # --- app.py: SearchScreen ---
    "search_help": {
        Lang.EN: "Enter search query (Enter confirm, Escape cancel)",
        Lang.KO: "검색어 입력 (Enter 확인, Escape 취소)",
    },
    "search_placeholder": {
        Lang.EN: "Search articles...",
        Lang.KO: "글 검색...",
    },
    # --- app.py: HawaiiDiscoApp status messages ---
    "refreshing": {Lang.EN: "Refreshing...", Lang.KO: "새로고침 중..."},
    "new_articles_found": {
        Lang.EN: "{count} new article(s) found",
        Lang.KO: "새 글 {count}개 발견",
    },
    "no_new_articles": {Lang.EN: "No new articles", Lang.KO: "새 글 없음"},
    "claude_cli_not_found": {
        Lang.EN: "Claude CLI not found",
        Lang.KO: "Claude CLI를 찾을 수 없습니다",
    },
    "generating_insight": {
        Lang.EN: "Generating insight...",
        Lang.KO: "인사이트 생성 중...",
    },
    "bookmark_added": {
        Lang.EN: "★ Bookmarked: {title}",
        Lang.KO: "★ 북마크 추가: {title}",
    },
    "bookmark_removed": {
        Lang.EN: "Bookmark removed: {title}",
        Lang.KO: "북마크 해제: {title}",
    },
    "bookmark_first": {
        Lang.EN: "Please bookmark first",
        Lang.KO: "먼저 북마크해주세요",
    },
    "memo_saved": {Lang.EN: "Memo saved", Lang.KO: "메모 저장됨"},
    "searching": {
        Lang.EN: "Search: {query}",
        Lang.KO: "검색: {query}",
    },
    "search_no_results": {
        Lang.EN: "No results for '{query}' (Escape to clear)",
        Lang.KO: "'{query}' 검색 결과 없음 (Escape로 해제)",
    },
    "search_cleared": {
        Lang.EN: "Search cleared",
        Lang.KO: "검색 해제됨",
    },
    "bookmarks_only": {
        Lang.EN: "★ Bookmarks only",
        Lang.KO: "★ 북마크만 보기",
    },
    "feed_added": {
        Lang.EN: "Feed added: {name}",
        Lang.KO: "피드 추가됨: {name}",
    },
    "already_translated": {
        Lang.EN: "Already translated (check detail panel)",
        Lang.KO: "이미 번역됨 (상세 패널에서 확인)",
    },
    "translated_preview": {
        Lang.EN: "Translated: {title}",
        Lang.KO: "번역: {title}",
    },
    "translation_failed": {
        Lang.EN: "Translation failed. Please try again.",
        Lang.KO: "번역에 실패했습니다. 다시 시도해주세요.",
    },
    # --- OPML ---
    "opml_import_help": {
        Lang.EN: "Enter OPML file path (Enter confirm, Escape cancel)",
        Lang.KO: "OPML 파일 경로 입력 (Enter 확인, Escape 취소)",
    },
    "opml_path_placeholder": {
        Lang.EN: "Path to .opml file",
        Lang.KO: ".opml 파일 경로",
    },
    "opml_import_success": {
        Lang.EN: "{count} feed(s) imported from OPML",
        Lang.KO: "OPML에서 {count}개 피드 가져옴",
    },
    "opml_import_empty": {
        Lang.EN: "No feeds found in OPML file",
        Lang.KO: "OPML 파일에서 피드를 찾을 수 없습니다",
    },
    "opml_import_error": {
        Lang.EN: "Failed to import OPML: {error}",
        Lang.KO: "OPML 가져오기 실패: {error}",
    },
    "opml_export_success": {
        Lang.EN: "Feeds exported to {path}",
        Lang.KO: "피드를 {path}에 내보냈습니다",
    },
    "opml_export_error": {
        Lang.EN: "Failed to export OPML: {error}",
        Lang.KO: "OPML 내보내기 실패: {error}",
    },
    "opml_no_feeds": {
        Lang.EN: "No feeds to export",
        Lang.KO: "내보낼 피드가 없습니다",
    },
    "opml_import": {Lang.EN: "Import OPML", Lang.KO: "OPML 가져오기"},
    "opml_export": {Lang.EN: "Export OPML", Lang.KO: "OPML 내보내기"},
    # --- Feed delete ---
    "confirm_delete_feed": {
        Lang.EN: "Delete feed '{name}'? ({count} articles will be removed)",
        Lang.KO: "피드 '{name}'을(를) 삭제하시겠습니까? ({count}개의 글이 삭제됩니다)",
    },
    "confirm_delete_hint": {
        Lang.EN: "y: confirm / n or Esc: cancel",
        Lang.KO: "y: 확인 / n 또는 Esc: 취소",
    },
    "feed_deleted": {
        Lang.EN: "Feed deleted: {name} ({count} articles removed)",
        Lang.KO: "피드 삭제됨: {name} ({count}개의 글 삭제)",
    },
    # --- Feed filter ---
    "feed_filter_active": {
        Lang.EN: "Feed: {name}",
        Lang.KO: "피드: {name}",
    },
    "feed_filter_cleared": {
        Lang.EN: "Feed filter cleared",
        Lang.KO: "피드 필터 해제됨",
    },
    # --- FeedListScreen / BookmarkListScreen ---
    "feed_list_title": {
        Lang.EN: "Subscribed Feeds",
        Lang.KO: "구독 피드 목록",
    },
    "no_feeds": {
        Lang.EN: "No feeds configured. Press 'a' to add a feed.",
        Lang.KO: "설정된 피드가 없습니다. 'a'를 눌러 추가하세요.",
    },
    "article_count": {
        Lang.EN: "{count} articles",
        Lang.KO: "{count}개의 글",
    },
    "feeds": {Lang.EN: "Feeds", Lang.KO: "피드목록"},
    "bookmark_list_title": {
        Lang.EN: "Bookmarked Articles",
        Lang.KO: "북마크 목록",
    },
    "no_bookmarks": {
        Lang.EN: "No bookmarked articles.",
        Lang.KO: "북마크된 글이 없습니다.",
    },
    "bookmarks_label": {Lang.EN: "Bookmarks", Lang.KO: "북마크"},
    # --- BookmarkListScreen: AI 분석 ---
    "bookmark_analysis_title": {
        Lang.EN: "Bookmark Analysis (Last 7 days)",
        Lang.KO: "북마크 분석 (최근 7일)",
    },
    "generating_bookmark_analysis": {
        Lang.EN: "Generating bookmark analysis...",
        Lang.KO: "북마크 분석 생성 중...",
    },
    "bookmark_analysis_complete": {
        Lang.EN: "Bookmark analysis complete",
        Lang.KO: "북마크 분석 완료",
    },
    "bookmark_analysis_failed": {
        Lang.EN: "Bookmark analysis failed",
        Lang.KO: "북마크 분석 생성 실패",
    },
    "no_recent_bookmarks": {
        Lang.EN: "No bookmarks in the last 7 days.",
        Lang.KO: "최근 7일간 북마크한 글이 없습니다.",
    },
    "bookmark_articles_section": {
        Lang.EN: "Bookmarked Articles",
        Lang.KO: "북마크 목록",
    },
    # --- widgets/status.py ---
    "nav_move": {Lang.EN: "↑↓ Move", Lang.KO: "↑↓ 이동"},
    "read": {Lang.EN: "Read", Lang.KO: "읽기"},
    "insight": {Lang.EN: "Insight", Lang.KO: "인사이트"},
    "bookmark": {Lang.EN: "Bookmark", Lang.KO: "북마크"},
    "refresh": {Lang.EN: "Refresh", Lang.KO: "새로고침"},
    "search": {Lang.EN: "Search", Lang.KO: "검색"},
    "filter": {Lang.EN: "Filter", Lang.KO: "필터"},
    "add_feed": {Lang.EN: "Add feed", Lang.KO: "피드추가"},
    "quit": {Lang.EN: "Quit", Lang.KO: "종료"},
    "last_refresh": {
        Lang.EN: "Last refresh: {time}",
        Lang.KO: "마지막 갱신: {time}",
    },
    # --- widgets/detail.py ---
    "select_article": {
        Lang.EN: "Select an article",
        Lang.KO: "글을 선택하세요",
    },
    # --- widgets/timeline.py ---
    "just_now": {Lang.EN: "just now", Lang.KO: "방금"},
    "minutes_ago": {
        Lang.EN: "{n}m ago",
        Lang.KO: "{n}분 전",
    },
    "hours_ago": {
        Lang.EN: "{n}h ago",
        Lang.KO: "{n}시간 전",
    },
    "days_ago": {
        Lang.EN: "{n}d ago",
        Lang.KO: "{n}일 전",
    },
    # --- reader.py ---
    "fetch_error": {
        Lang.EN: "Could not fetch page ({error})",
        Lang.KO: "페이지를 가져올 수 없습니다 ({error})",
    },
    "extract_error": {
        Lang.EN: "Could not extract content.",
        Lang.KO: "본문을 추출할 수 없습니다.",
    },
    "truncated": {
        Lang.EN: "... (truncated)",
        Lang.KO: "... (이하 생략)",
    },
    # --- fetcher.py ---
    "no_title": {Lang.EN: "(No title)", Lang.KO: "(제목 없음)"},
    # --- bookmark.py ---
    "bm_source": {Lang.EN: "Source", Lang.KO: "출처"},
    "bm_date": {Lang.EN: "Date", Lang.KO: "날짜"},
    "bm_link": {Lang.EN: "Link", Lang.KO: "링크"},
    "bm_insight": {Lang.EN: "Insight", Lang.KO: "인사이트"},
    "bm_memo_section": {Lang.EN: "## Memo", Lang.KO: "## 메모"},
    "bm_no_memo": {Lang.EN: "(No memo)", Lang.KO: "(메모 없음)"},
    # --- insight.py ---
    "insight_failed": {
        Lang.EN: "Insight generation failed",
        Lang.KO: "인사이트 생성 실패",
    },
    # --- translate.py ---
    "translation_failed_short": {
        Lang.EN: "Translation failed",
        Lang.KO: "번역 실패",
    },
    # --- Tag ---
    "tag_edit_help": {
        Lang.EN: "Enter tags separated by commas (Enter save, Escape cancel)",
        Lang.KO: "태그를 쉼표로 구분하여 입력 (Enter 저장, Escape 취소)",
    },
    "tag_placeholder": {
        Lang.EN: "e.g. tech, python, ai",
        Lang.KO: "예: tech, python, ai",
    },
    "tag_saved": {
        Lang.EN: "Tags saved",
        Lang.KO: "태그 저장됨",
    },
    "tag_list_title": {
        Lang.EN: "Tags",
        Lang.KO: "태그 목록",
    },
    "no_tags": {
        Lang.EN: "No tags yet. Press 'c' on a bookmarked article to add tags.",
        Lang.KO: "태그가 없습니다. 북마크된 글에서 'c'를 눌러 태그를 추가하세요.",
    },
    "tag_count": {
        Lang.EN: "{count} articles",
        Lang.KO: "{count}개의 글",
    },
    "tag_filter_active": {
        Lang.EN: "Tag: {tag}",
        Lang.KO: "태그: {tag}",
    },
    "tag_filter_cleared": {
        Lang.EN: "Tag filter cleared",
        Lang.KO: "태그 필터 해제됨",
    },
    "bookmark_first_for_tag": {
        Lang.EN: "Bookmark the article first to add tags",
        Lang.KO: "태그를 추가하려면 먼저 북마크하세요",
    },
    "tags_label": {Lang.EN: "Tags", Lang.KO: "태그"},
    # --- Theme ---
    "theme_list_title": {
        Lang.EN: "Select Theme",
        Lang.KO: "테마 선택",
    },
    "theme_applied": {
        Lang.EN: "Theme: {name}",
        Lang.KO: "테마: {name}",
    },
    "theme_dark": {Lang.EN: "dark", Lang.KO: "다크"},
    "theme_light": {Lang.EN: "light", Lang.KO: "라이트"},
    "theme_label": {Lang.EN: "Theme", Lang.KO: "테마"},
}


def set_lang(lang: str) -> None:
    """Set the current language."""
    global _current_lang
    try:
        _current_lang = Lang(lang)
    except ValueError:
        _current_lang = Lang.EN


def get_lang() -> Lang:
    """Return the current language."""
    return _current_lang


def t(key: str, **kwargs: object) -> str:
    """Return the localized string for the given key in the current language."""
    entry = _STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(_current_lang) or entry.get(Lang.EN, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
