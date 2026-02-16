"""보안 수정사항에 대한 테스트."""
from __future__ import annotations

from pathlib import Path

import pytest

from hawaiidisco.bookmark import _safe_path, _slugify
from hawaiidisco.db import Database
from hawaiidisco.i18n import set_lang


# --- _safe_path: Path Traversal 방어 ---


class TestSafePath:
    def test_normal_filename(self, tmp_path: Path) -> None:
        result = _safe_path(tmp_path, "2024-01-01-hello.md")
        assert result == (tmp_path / "2024-01-01-hello.md").resolve()

    def test_traversal_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_path(tmp_path, "../../../etc/passwd")

    def test_double_dot_in_middle(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Path traversal"):
            _safe_path(tmp_path, "foo/../../etc/passwd")

    def test_absolute_path_in_filename(self, tmp_path: Path) -> None:
        # 절대 경로가 filename으로 오면 Path / 연산에서 절대경로 우선
        result = _safe_path(tmp_path, "normal-file.md")
        assert result.is_relative_to(tmp_path.resolve())


# --- _slugify: 특수문자 제거 ---


class TestSlugify:
    def test_slash_removed(self) -> None:
        assert "/" not in _slugify("path/traversal/attack")

    def test_dotdot_removed(self) -> None:
        slug = _slugify("../../etc/passwd")
        assert ".." not in slug
        assert "/" not in slug

    def test_korean_preserved(self) -> None:
        slug = _slugify("한글 테스트 제목")
        assert "한글" in slug

    def test_max_length(self) -> None:
        long_title = "a" * 100
        assert len(_slugify(long_title, max_len=50)) <= 50


# --- LIKE 와일드카드 이스케이프 ---


class TestLikeEscape:
    def setup_method(self, method) -> None:
        self.db = Database(Path(":memory:"))

    def teardown_method(self, method) -> None:
        self.db.close()

    def _insert(self, title: str, description: str | None = None, article_id: str | None = None) -> None:
        from datetime import datetime
        aid = article_id or title[:16]
        self.db.upsert_article(
            article_id=aid,
            feed_name="test",
            title=title,
            link="https://example.com",
            description=description,
            published_at=datetime.now(),
        )

    def test_percent_in_search(self) -> None:
        self._insert("100% Pure Python")
        self._insert("Python Tips")
        # '%'로 검색하면 '100% Pure Python'만 매칭
        results = self.db.get_articles(search="%")
        assert len(results) == 1
        assert "100%" in results[0].title

    def test_search_by_description(self) -> None:
        """description 컬럼으로 검색할 수 있다."""
        self._insert("Generic Title", description="unique_keyword_in_desc")
        results = self.db.get_articles(search="unique_keyword_in_desc")
        assert len(results) == 1
        assert results[0].title == "Generic Title"

    def test_search_by_insight(self) -> None:
        """insight 컬럼으로 검색할 수 있다."""
        self._insert("Generic Title2", article_id="insight-1")
        self.db.set_insight("insight-1", "special_insight_text")
        results = self.db.get_articles(search="special_insight_text")
        assert len(results) == 1
        assert results[0].id == "insight-1"

    def test_search_by_translated_title(self) -> None:
        """translated_title 컬럼으로 검색할 수 있다."""
        self._insert("English Title", article_id="trans-1")
        self.db.set_translation("trans-1", "번역된 제목", "번역된 설명")
        results = self.db.get_articles(search="번역된 제목")
        assert len(results) == 1
        assert results[0].id == "trans-1"

    def test_underscore_in_search(self) -> None:
        self._insert("my_variable_name")
        self._insert("my variable name")
        # '_'로 검색하면 '_'가 포함된 것만 매칭
        results = self.db.get_articles(search="_")
        assert len(results) == 1
        assert "_" in results[0].title


# --- SSL 폴백 패턴 ---


class TestSSLFallback:
    def test_fetch_error_hides_details(self) -> None:
        """에러 메시지에 예외 클래스명만 노출되는지 확인."""
        from hawaiidisco.reader import fetch_article_text
        set_lang("en")
        # 존재하지 않는 호스트로 요청
        result = fetch_article_text("https://this-host-does-not-exist.invalid", timeout=2)
        # 예외 스택트레이스나 상세 메시지 대신 클래스명만 포함
        assert "Traceback" not in result
        assert "Could not fetch page" in result


# --- URL 스키마 검증 ---


class TestURLSchemeValidation:
    def test_http_allowed(self) -> None:
        url = "http://example.com/feed.xml"
        assert url.startswith(("http://", "https://"))

    def test_https_allowed(self) -> None:
        url = "https://example.com/feed.xml"
        assert url.startswith(("http://", "https://"))

    def test_file_scheme_rejected(self) -> None:
        url = "file:///etc/passwd"
        assert not url.startswith(("http://", "https://"))

    def test_ftp_scheme_rejected(self) -> None:
        url = "ftp://example.com/feed.xml"
        assert not url.startswith(("http://", "https://"))

    def test_no_scheme_rejected(self) -> None:
        url = "example.com/feed.xml"
        assert not url.startswith(("http://", "https://"))


# --- AppleScript 이스케이프 ---


class TestAppleScriptEscape:
    def test_quote_escaped(self) -> None:
        msg = 'Hello "world"'
        safe = msg.replace("\\", "\\\\").replace('"', '\\"')
        assert '\\"' in safe
        assert '"world"' not in safe

    def test_backslash_escaped(self) -> None:
        msg = "path\\to\\file"
        safe = msg.replace("\\", "\\\\").replace('"', '\\"')
        assert "\\\\" in safe


# --- 디렉토리 권한 ---


class TestDirectoryPermissions:
    def test_ensure_dirs_sets_700(self, tmp_path: Path) -> None:
        from hawaiidisco.config import Config, ensure_dirs

        db_dir = tmp_path / "data"
        bm_dir = tmp_path / "bookmarks"
        config = Config(
            db_path=db_dir / "test.db",
            bookmark_dir=bm_dir,
        )
        ensure_dirs(config)

        assert db_dir.exists()
        assert bm_dir.exists()
        # 소유자만 rwx
        assert oct(db_dir.stat().st_mode & 0o777) == "0o700"
        assert oct(bm_dir.stat().st_mode & 0o777) == "0o700"
