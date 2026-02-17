"""Textual main application."""
from __future__ import annotations

import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path


from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches

from hawaiidisco.ai import get_provider
from hawaiidisco.config import Config, FeedConfig, load_config, ensure_dirs, add_feed, remove_feed
from hawaiidisco.opml import parse_opml, export_opml
from hawaiidisco.i18n import t
from hawaiidisco.reader import fetch_article_text
from hawaiidisco.db import Article, Database
from hawaiidisco.fetcher import fetch_all_feeds
from hawaiidisco.insight import get_or_generate_insight
from hawaiidisco.bookmark import save_bookmark_md, delete_bookmark_md
from hawaiidisco.obsidian import save_obsidian_note, save_digest_note, delete_obsidian_note, validate_vault_path
from hawaiidisco.digest import get_or_generate_digest
from hawaiidisco.translate import translate_article_meta, translate_text
from hawaiidisco.widgets.timeline import Timeline
from hawaiidisco.widgets.detail import DetailView
from hawaiidisco.widgets.status import StatusBar
from hawaiidisco.screens import (
    MemoScreen,
    ArticleScreen,
    AddFeedScreen,
    FeedListScreen,
    BookmarkListScreen,
    OpmlImportScreen,
    TagEditScreen,
    TagListScreen,
    ThemeListScreen,
    SearchScreen,
    DigestScreen,
)


class HawaiiDiscoApp(App):
    """Hawaii Disco - Terminal RSS Reader."""

    TITLE = "Hawaii Disco"
    CSS = """
    Timeline {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("b", "bookmark", "Bookmark"),
        Binding("m", "memo", "Memo"),
        Binding("enter", "read_article", "Read", show=False),
        Binding("space", "read_article", "Read", show=False),
        Binding("o", "open_browser", "Browser"),
        Binding("l", "bookmark_list", "Bookmarks"),
        Binding("slash", "search", "Search"),
        Binding("escape", "clear_search", "Clear search", show=False),
        Binding("f", "filter_bookmarks", "Filter"),
        Binding("u", "filter_unread", "Unread"),
        Binding("a", "add_feed", "Add feed"),
        Binding("L", "feed_list", "Feeds"),
        Binding("t", "translate", "Translate"),
        Binding("c", "edit_tags", "Tags"),
        Binding("T", "tag_list", "Tag list"),
        Binding("S", "save_obsidian", t("save_to_obsidian")),
        Binding("V", "select_theme", "Theme"),
        Binding("I", "import_opml", "Import OPML"),
        Binding("E", "export_opml", "Export OPML"),
        Binding("D", "digest", t("digest_label")),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.config: Config = load_config()
        ensure_dirs(self.config)
        self.db = Database(self.config.db_path)
        self.ai = get_provider(self.config.ai)
        self._current_article: Article | None = None
        self._bookmark_filter: bool = False
        self._search_query: str | None = None
        self._feed_filter: str | None = None
        self._tag_filter: str | None = None
        self._unread_filter: bool = False
        self.theme = self.config.theme

        # Validate Obsidian vault path at startup
        if self.config.obsidian.enabled and not validate_vault_path(self.config.obsidian):
            import sys

            print(
                f"Warning: Obsidian vault path not found: {self.config.obsidian.vault_path}",
                file=sys.stderr,
            )

    def compose(self) -> ComposeResult:
        yield Timeline([], id="timeline")
        yield DetailView()
        yield StatusBar()

    def on_mount(self) -> None:
        self._do_refresh()

    # --- Event Handlers ---

    def on_timeline_article_highlighted(self, event: Timeline.ArticleHighlighted) -> None:
        self._current_article = event.article
        try:
            self.query_one(DetailView).show_article(event.article)
        except NoMatches:
            pass

    def on_timeline_article_selected(self, event: Timeline.ArticleSelected) -> None:
        self._read_article(event.article)

    # --- Actions ---

    def action_refresh(self) -> None:
        self._do_refresh()

    @work(thread=True)
    def _do_refresh(self) -> None:
        """Fetch feeds in the background."""
        try:
            status = self.query_one(StatusBar)
        except NoMatches:
            return
        self.call_from_thread(status.set_message, t("refreshing"))

        new_count = fetch_all_feeds(self.config.feeds, self.db, allow_insecure_ssl=self.config.allow_insecure_ssl)
        now = datetime.now()

        if new_count > 0:
            msg = t("new_articles_found", count=new_count)
            self._notify_macos(msg)
        else:
            msg = t("no_new_articles")

        self.call_from_thread(status.set_message, msg)
        self.call_from_thread(status.set_last_refresh, now)
        self.call_from_thread(self._reload_articles)

        # Clear message after a short delay
        import time
        time.sleep(3)
        self.call_from_thread(status.set_message, "")

    def _reload_articles(self) -> None:
        """Reload the article list according to current filter settings."""
        if self._tag_filter:
            articles = self.db.get_articles_by_tag(self._tag_filter)
        else:
            articles = self.db.get_articles(
                bookmarked_only=self._bookmark_filter,
                search=self._search_query,
                feed_name=self._feed_filter,
                unread_only=self._unread_filter,
            )
        # 태그 정보를 일괄 조회하여 Timeline에 전달
        all_tags = self.db.get_all_bookmark_tags()
        try:
            timeline = self.query_one(Timeline)
        except NoMatches:
            return
        timeline.refresh_articles(articles, all_tags)

    def action_read_article(self) -> None:
        article = self._get_current_article()
        if article:
            self._read_article(article)

    def _read_article(self, article: Article) -> None:
        """Display the article body in the TUI."""
        self.db.mark_read(article.id)
        self._reload_articles()

        meta = f"{article.feed_name}"
        if article.published_at:
            meta += f" · {article.published_at.strftime('%Y-%m-%d %H:%M')}"
        meta += f"\n{article.link}"

        # Open screen with description first, then fetch full text in background
        screen = ArticleScreen(
            title=article.title,
            meta=meta,
            body=article.description or t("loading_body"),
            link=article.link,
            article_id=article.id,
            translated_body=article.translated_body,
            description=article.description,
            insight=article.insight,
        )
        self.push_screen(screen)
        self._fetch_full_article(article.link, screen)

    @work(thread=True)
    def _fetch_full_article(self, url: str, screen: ArticleScreen) -> None:
        text = fetch_article_text(url, allow_insecure_ssl=self.config.allow_insecure_ssl)
        self.call_from_thread(screen.update_body, text)

    def action_open_browser(self) -> None:
        article = self._get_current_article()
        if article and article.link.startswith(("http://", "https://")):
            self.db.mark_read(article.id)
            webbrowser.open(article.link)
            self._reload_articles()

    @work(thread=True)
    def _generate_insight_for_screen(self, screen: ArticleScreen) -> None:
        """Generate insight for an ArticleScreen. Check DB cache first, generate if missing."""
        article_id = screen._article_id

        if not self.ai.is_available():
            self.call_from_thread(screen.update_insight, t("claude_cli_not_found"))
            return

        # Check DB cache
        if article_id:
            cached = self.db.get_article(article_id)
            if cached and cached.insight:
                self.call_from_thread(screen.update_insight, cached.insight)
                return

        # Build Article object from description and generate insight
        if article_id:
            article = self.db.get_article(article_id)
        else:
            article = None

        if article:
            insight = get_or_generate_insight(article, self.db, self.ai)
            self.call_from_thread(screen.update_insight, insight)
            self.call_from_thread(self._reload_articles)

            # Refresh detail view on main screen
            updated = self.db.get_article(article_id)
            if updated:
                try:
                    detail = self.query_one(DetailView)
                    self.call_from_thread(detail.show_article, updated)
                except NoMatches:
                    pass
        else:
            self.call_from_thread(screen.update_insight, t("insight_failed"))

    def action_bookmark(self) -> None:
        article = self._get_current_article()
        if not article:
            return
        new_state = self.db.toggle_bookmark(article.id)
        status = self.query_one(StatusBar)

        if new_state:
            updated = self.db.get_article(article.id)
            if updated:
                save_bookmark_md(updated, self.config.bookmark_dir)
                # Auto-save to Obsidian if enabled
                if self.config.obsidian.enabled and self.config.obsidian.auto_save:
                    if validate_vault_path(self.config.obsidian):
                        try:
                            tags = self.db.get_bookmark_tags(article.id)
                            save_obsidian_note(updated, self.config.obsidian, tags=tags)
                            status.set_message(t("obsidian_auto_saved", title=article.title[:30]))
                            self._reload_articles()
                            return
                        except Exception:
                            pass  # Fall through to standard bookmark message
            status.set_message(t("bookmark_added", title=article.title[:30]))
        else:
            delete_bookmark_md(article, self.config.bookmark_dir)
            if self.config.obsidian.enabled and self.config.obsidian.auto_save:
                if validate_vault_path(self.config.obsidian):
                    try:
                        delete_obsidian_note(article, self.config.obsidian)
                    except Exception:
                        pass
            status.set_message(t("bookmark_removed", title=article.title[:30]))

        self._reload_articles()

    def action_memo(self) -> None:
        article = self._get_current_article()
        if not article or not article.is_bookmarked:
            self.query_one(StatusBar).set_message(t("bookmark_first"))
            return

        current_memo = self.db.get_bookmark_memo(article.id) or ""
        self.push_screen(MemoScreen(current_memo), self._on_memo_result)

    def _on_memo_result(self, memo: str) -> None:
        article = self._get_current_article()
        if not article or not memo:
            return
        self.db.set_bookmark_memo(article.id, memo)
        updated = self.db.get_article(article.id)
        if updated:
            save_bookmark_md(updated, self.config.bookmark_dir, memo)
            # Update Obsidian note too
            if self.config.obsidian.enabled and self.config.obsidian.auto_save:
                if validate_vault_path(self.config.obsidian):
                    try:
                        tags = self.db.get_bookmark_tags(article.id)
                        save_obsidian_note(updated, self.config.obsidian, memo=memo, tags=tags)
                    except Exception:
                        pass
        self.query_one(StatusBar).set_message(t("memo_saved"))

    def action_save_obsidian(self) -> None:
        """Manually save the current article to Obsidian vault."""
        article = self._get_current_article()
        if not article:
            return
        if not self.config.obsidian.enabled:
            self.query_one(StatusBar).set_message(t("obsidian_not_configured"))
            return
        if not validate_vault_path(self.config.obsidian):
            self.query_one(StatusBar).set_message(
                t("obsidian_vault_not_found", path=str(self.config.obsidian.vault_path))
            )
            return

        updated = self.db.get_article(article.id)
        if not updated:
            return

        memo = self.db.get_bookmark_memo(article.id)
        tags = self.db.get_bookmark_tags(article.id)

        try:
            save_obsidian_note(updated, self.config.obsidian, memo=memo, tags=tags)
            self.query_one(StatusBar).set_message(
                t("obsidian_saved", title=article.title[:30])
            )
        except Exception as exc:
            self.query_one(StatusBar).set_message(
                t("obsidian_save_failed", error=type(exc).__name__)
            )

    def action_search(self) -> None:
        self.push_screen(SearchScreen(), self._on_search_result)

    def _on_search_result(self, query: str) -> None:
        if query:
            self._search_query = query
            self._reload_articles()
            # 검색 결과가 없으면 안내 메시지 표시
            timeline = self.query_one(Timeline)
            if len(timeline) == 0:
                self.query_one(StatusBar).set_message(
                    t("search_no_results", query=query)
                )
            else:
                self.query_one(StatusBar).set_message(t("searching", query=query))
        else:
            self._search_query = None
            self.query_one(StatusBar).set_message("")
            self._reload_articles()

    def action_clear_search(self) -> None:
        """검색, 태그 필터, 피드 필터, 안읽은글 필터, 북마크 필터를 해제하고 원래 리스트로 복원."""
        if self._search_query is not None:
            self._search_query = None
            self.query_one(StatusBar).set_message(t("search_cleared"))
            self._reload_articles()
        elif self._tag_filter is not None:
            self._tag_filter = None
            self.query_one(StatusBar).set_message(t("tag_filter_cleared"))
            self._reload_articles()
        elif self._feed_filter is not None:
            self._feed_filter = None
            self.query_one(StatusBar).set_message(t("feed_filter_cleared"))
            self._reload_articles()
        elif self._unread_filter:
            self._unread_filter = False
            self.query_one(StatusBar).set_message(t("unread_filter_cleared"))
            self._reload_articles()
        elif self._bookmark_filter:
            self._bookmark_filter = False
            self.query_one(StatusBar).set_message("")
            self._reload_articles()

    def action_filter_bookmarks(self) -> None:
        self._bookmark_filter = not self._bookmark_filter
        status = self.query_one(StatusBar)
        if self._bookmark_filter:
            status.set_message(t("bookmarks_only"))
        else:
            status.set_message("")
        self._reload_articles()

    def action_filter_unread(self) -> None:
        self._unread_filter = not self._unread_filter
        status = self.query_one(StatusBar)
        if self._unread_filter:
            status.set_message(t("unread_only"))
        else:
            status.set_message("")
        self._reload_articles()

    def action_add_feed(self) -> None:
        self.push_screen(AddFeedScreen(), self._on_add_feed_result)

    def _on_add_feed_result(self, result: tuple) -> None:
        if not result:
            return
        url, name = result
        feed = FeedConfig(url=url, name=name)
        # Save to config.yml
        add_feed(feed)
        # Also add to in-memory config
        if not any(f.url == url for f in self.config.feeds):
            self.config.feeds.append(feed)
        self.query_one(StatusBar).set_message(t("feed_added", name=name))
        # Fetch the new feed immediately
        self._do_refresh()

    def action_feed_list(self) -> None:
        """Open the feed list screen."""
        counts = self.db.get_article_count_by_feed()
        self.push_screen(
            FeedListScreen(self.config.feeds, counts),
            self._on_feed_list_result,
        )

    def _on_feed_list_result(self, feed_name: str | None) -> None:
        """피드 선택 결과로 필터를 적용한다."""
        if feed_name:
            self._feed_filter = feed_name
            self.query_one(StatusBar).set_message(t("feed_filter_active", name=feed_name))
            self._reload_articles()
        # None이면 아무 작업 안 함 (ESC/q로 닫은 경우)

    def _do_delete_feed(self, feed: FeedConfig) -> None:
        """피드를 config.yml과 DB에서 삭제하고 UI를 갱신한다."""
        # config.yml에서 제거
        remove_feed(feed.url)
        # 인메모리 config에서 제거
        self.config.feeds = [f for f in self.config.feeds if f.url != feed.url]
        # DB에서 해당 피드 글 삭제
        deleted_count = self.db.delete_articles_by_feed(feed.name)
        # 피드 필터가 삭제된 피드면 해제
        if self._feed_filter == feed.name:
            self._feed_filter = None
        # UI 갱신
        self.query_one(StatusBar).set_message(
            t("feed_deleted", name=feed.name, count=deleted_count)
        )
        self._reload_articles()

    def action_bookmark_list(self) -> None:
        """Open the bookmark list screen."""
        articles = self.db.get_articles(bookmarked_only=True)
        memos = self.db.get_all_bookmark_memos()
        tags = self.db.get_all_bookmark_tags()
        screen = BookmarkListScreen(articles, memos, tags)
        self.push_screen(screen, self._on_bookmark_list_result)
        if articles:
            self._generate_bookmark_analysis(screen, articles)

    @work(thread=True)
    def _generate_bookmark_analysis(
        self, screen: BookmarkListScreen, articles: list[Article]
    ) -> None:
        """북마크 컬렉션에 대한 AI 분석을 생성한다."""
        if not self.ai.is_available():
            self.call_from_thread(screen.update_analysis, t("claude_cli_not_found"))
            return

        from hawaiidisco.ai.prompts import (
            BOOKMARK_ANALYSIS_PROMPT,
            BOOKMARK_ANALYSIS_ITEM,
            NONE_TEXT,
            get_lang_name,
        )
        from hawaiidisco.i18n import get_lang

        lang = get_lang().value

        bookmarks_text = "\n".join(
            BOOKMARK_ANALYSIS_ITEM.format(
                title=a.title,
                description=a.description or NONE_TEXT,
                insight=a.insight or NONE_TEXT,
            )
            for a in articles
        )

        prompt = BOOKMARK_ANALYSIS_PROMPT.format(
            output_language=get_lang_name(lang),
            bookmarks=bookmarks_text,
        )

        result = self.ai.generate(prompt, timeout=60)
        try:
            status = self.query_one(StatusBar)
        except NoMatches:
            return
        if result:
            self.call_from_thread(screen.update_analysis, result)
            self.call_from_thread(status.set_message, t("bookmark_analysis_complete"))
        else:
            self.call_from_thread(screen.update_analysis, t("bookmark_analysis_failed"))
            self.call_from_thread(status.set_message, t("bookmark_analysis_failed"))

    def _on_bookmark_list_result(self, article_id: str | None) -> None:
        """Open the article selected from the bookmark list."""
        if not article_id:
            return
        article = self.db.get_article(article_id)
        if article:
            self._read_article(article)

    def action_import_opml(self) -> None:
        """OPML 파일에서 피드를 가져온다."""
        self.push_screen(OpmlImportScreen(), self._on_opml_import_result)

    def _on_opml_import_result(self, path_str: str) -> None:
        if not path_str:
            return
        try:
            path = Path(path_str).expanduser().resolve()
            feeds = parse_opml(path)
        except Exception as e:
            self.query_one(StatusBar).set_message(
                t("opml_import_error", error=type(e).__name__)
            )
            return

        if not feeds:
            self.query_one(StatusBar).set_message(t("opml_import_empty"))
            return

        added = 0
        for feed in feeds:
            if not any(f.url == feed.url for f in self.config.feeds):
                add_feed(feed)
                self.config.feeds.append(feed)
                added += 1

        self.query_one(StatusBar).set_message(
            t("opml_import_success", count=added)
        )
        if added > 0:
            self._do_refresh()

    def action_export_opml(self) -> None:
        """현재 피드 목록을 OPML 파일로 내보낸다."""
        if not self.config.feeds:
            self.query_one(StatusBar).set_message(t("opml_no_feeds"))
            return
        try:
            output_path = Path("~/.local/share/hawaiidisco/feeds.opml").expanduser()
            result_path = export_opml(self.config.feeds, output_path)
            self.query_one(StatusBar).set_message(
                t("opml_export_success", path=str(result_path))
            )
        except Exception as e:
            self.query_one(StatusBar).set_message(
                t("opml_export_error", error=type(e).__name__)
            )

    # --- Tag Actions ---

    def action_edit_tags(self) -> None:
        """북마크된 글에 태그를 편집한다."""
        article = self._get_current_article()
        if not article:
            return
        if not article.is_bookmarked:
            self.query_one(StatusBar).set_message(t("bookmark_first_for_tag"))
            return
        current_tags = self.db.get_bookmark_tags(article.id)
        self.push_screen(
            TagEditScreen(", ".join(current_tags)),
            self._on_tag_edit_result,
        )

    def _on_tag_edit_result(self, result: str) -> None:
        article = self._get_current_article()
        if not article or not result and result != "":
            return
        # result가 빈 문자열이면 dismiss(ESC) → 무시
        if result == "":
            return
        tags = [t_tag.strip() for t_tag in result.split(",") if t_tag.strip()]
        self.db.set_bookmark_tags(article.id, tags)
        self.query_one(StatusBar).set_message(t("tag_saved"))
        self._reload_articles()

    def action_tag_list(self) -> None:
        """태그 목록을 보여주고 선택하면 필터링한다."""
        all_tags = self.db.get_all_tags()
        if not all_tags:
            self.query_one(StatusBar).set_message(t("no_tags"))
            return
        # 각 태그별 글 수 계산
        tags_with_counts = [
            (tag, len(self.db.get_articles_by_tag(tag))) for tag in all_tags
        ]
        self.push_screen(
            TagListScreen(tags_with_counts),
            self._on_tag_list_result,
        )

    def _on_tag_list_result(self, tag: str | None) -> None:
        if tag:
            self._tag_filter = tag
            self.query_one(StatusBar).set_message(t("tag_filter_active", tag=tag))
            self._reload_articles()

    # --- Theme Actions ---

    def action_select_theme(self) -> None:
        """테마 선택 화면을 연다."""
        themes: list[tuple[str, bool]] = []
        for name, theme_obj in self.available_themes.items():
            if name == "textual-ansi":
                continue
            themes.append((name, theme_obj.dark))
        # 다크 테마를 먼저, 이름순 정렬
        themes.sort(key=lambda x: (not x[1], x[0]))
        self.push_screen(
            ThemeListScreen(themes, self.theme),
            self._on_theme_result,
        )

    def _on_theme_result(self, theme_name: str | None) -> None:
        if theme_name:
            self.theme = theme_name
            self.query_one(StatusBar).set_message(t("theme_applied", name=theme_name))

    def action_translate(self) -> None:
        """Translate the title/description of the selected article in the timeline."""
        article = self._get_current_article()
        if not article:
            return
        # Already translated
        if article.translated_title:
            self.query_one(StatusBar).set_message(t("already_translated"))
            return
        if not self.ai.is_available():
            self.query_one(StatusBar).set_message(t("claude_cli_not_found"))
            return
        self._do_translate(article)

    @work(thread=True)
    def _do_translate(self, article: Article) -> None:
        try:
            status = self.query_one(StatusBar)
        except NoMatches:
            return
        self.call_from_thread(status.set_message, t("translating"))

        t_title, t_desc = translate_article_meta(article.title, article.description, self.ai)
        self.db.set_translation(article.id, t_title, t_desc)

        self.call_from_thread(status.set_message, t("translated_preview", title=t_title[:40]))
        self.call_from_thread(self._reload_articles)

        updated = self.db.get_article(article.id)
        if updated:
            try:
                detail = self.query_one(DetailView)
                self.call_from_thread(detail.show_article, updated)
            except NoMatches:
                pass

    @work(thread=True)
    def _translate_article_body(self, screen: ArticleScreen) -> None:
        """Translate the article body for an ArticleScreen. Check DB cache first, generate if missing."""
        article_id = screen._article_id

        # Check DB cache
        if article_id:
            cached = self.db.get_translated_body(article_id)
            if cached:
                self.call_from_thread(screen.update_translated_body, cached)
                return

        # Generate translation
        translated = translate_text(screen._body, self.ai, timeout=60)
        if translated:
            # Save to DB
            if article_id:
                self.db.set_translated_body(article_id, translated)
            # Update UI (DOM access must happen inside call_from_thread callback)
            self.call_from_thread(screen.update_translated_body, translated)
        else:
            self.call_from_thread(
                screen.update_translated_body, t("translation_failed")
            )

    # --- Digest Actions ---

    def action_digest(self) -> None:
        """Generate and display a weekly article digest."""
        if not self.config.digest.enabled:
            self.query_one(StatusBar).set_message(t("digest_not_enabled"))
            return
        screen = DigestScreen()
        self.push_screen(screen)
        self._generate_digest(screen)

    @work(thread=True)
    def _generate_digest(self, screen: DigestScreen) -> None:
        """Generate digest in background thread."""
        try:
            content, article_count = get_or_generate_digest(
                self.db, self.ai, self.config.digest
            )
            self.call_from_thread(screen.update_content, content, article_count)
            try:
                status = self.query_one(StatusBar)
                self.call_from_thread(status.set_message, t("digest_complete"))
            except NoMatches:
                pass
        except ValueError as exc:
            self.call_from_thread(screen.update_error, str(exc))
        except Exception:
            self.call_from_thread(screen.update_error, t("digest_generation_failed"))

    def _save_digest_to_obsidian(self, content: str, article_count: int) -> None:
        """Save digest to Obsidian vault."""
        if not self.config.obsidian.enabled:
            self.query_one(StatusBar).set_message(t("obsidian_not_configured"))
            return
        if not validate_vault_path(self.config.obsidian):
            self.query_one(StatusBar).set_message(
                t("obsidian_vault_not_found", path=str(self.config.obsidian.vault_path))
            )
            return
        try:
            save_digest_note(
                content, article_count, self.config.obsidian, self.config.digest.period_days
            )
            self.query_one(StatusBar).set_message(t("digest_saved_obsidian"))
        except Exception as exc:
            self.query_one(StatusBar).set_message(
                t("obsidian_save_failed", error=type(exc).__name__)
            )

    # --- Background Auto-Refresh ---

    def on_ready(self) -> None:
        """Set up the auto-refresh timer after the app is ready."""
        interval_seconds = self.config.refresh_interval * 60
        self.set_interval(interval_seconds, self._auto_refresh)

    def _auto_refresh(self) -> None:
        self._do_refresh()

    # --- Utilities ---

    def _get_current_article(self) -> Article | None:
        try:
            timeline = self.query_one(Timeline)
        except NoMatches:
            return None
        return timeline.get_highlighted_article()

    def _notify_macos(self, message: str) -> None:
        """Send a macOS notification."""
        # AppleScript 인젝션 방지: 백슬래시와 큰따옴표 이스케이프
        safe_msg = message.replace("\\", "\\\\").replace('"', '\\"')
        try:
            subprocess.Popen(
                [
                    "osascript", "-e",
                    f'display notification "{safe_msg}" with title "Hawaii Disco"',
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (FileNotFoundError, OSError):
            pass

    def on_unmount(self) -> None:
        self.db.close()


def main() -> None:
    app = HawaiiDiscoApp()
    app.run()


if __name__ == "__main__":
    main()
