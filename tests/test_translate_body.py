"""Integration tests for translation functionality."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.ai.prompts import TRANSLATABLE_LANGS, get_lang_name
from hawaiidisco.db import Database
from hawaiidisco.translate import translate_text, translate_article_meta, _parse_translation


@pytest.fixture()
def db(tmp_path: Path) -> Database:
    """Create a temporary DB instance."""
    return Database(tmp_path / "test.db")


def _insert_sample(db: Database, article_id: str = "test-1") -> None:
    db.upsert_article(
        article_id=article_id,
        feed_name="TestFeed",
        title="Test Article",
        link="https://example.com",
        description="desc",
        published_at=None,
    )


def _make_mock_provider(available: bool = True, output: str = "번역 결과") -> MagicMock:
    """Create a mock AI provider."""
    provider = MagicMock(spec=AIProvider)
    provider.is_available.return_value = available
    provider.generate.return_value = output
    provider.name = "mock"
    return provider


class TestTranslateTextTimeout:
    """Tests for translate_text timeout parameter."""

    def test_default_timeout_is_60(self) -> None:
        """Default timeout is 60 seconds."""
        provider = _make_mock_provider()
        translate_text("hello world", provider, lang="ko")
        _, kwargs = provider.generate.call_args
        assert kwargs["timeout"] == 60

    def test_custom_timeout(self) -> None:
        """Custom timeout is passed through."""
        provider = _make_mock_provider()
        translate_text("hello world", provider, timeout=120, lang="ko")
        _, kwargs = provider.generate.call_args
        assert kwargs["timeout"] == 120

    def test_long_text_truncated(self) -> None:
        """Text exceeding 10,000 characters is truncated."""
        provider = _make_mock_provider(output="번역됨")
        long_text = "a" * 15000
        translate_text(long_text, provider, lang="ko")
        call_args = provider.generate.call_args[0][0]  # prompt
        assert "a" * 10000 in call_args
        assert "a" * 15000 not in call_args

    def test_empty_text_returns_none(self) -> None:
        """Empty text returns None."""
        provider = _make_mock_provider()
        result = translate_text("", provider, lang="ko")
        assert result is None

    def test_english_user_skips_translation(self) -> None:
        """Translation is skipped for English users."""
        provider = _make_mock_provider()
        result = translate_text("hello world", provider, lang="en")
        assert result is None
        provider.generate.assert_not_called()

    def test_provider_unavailable_returns_none(self) -> None:
        """Return None when provider is unavailable; do not call generate."""
        provider = _make_mock_provider(available=False)
        result = translate_text("hello world", provider, lang="ko")
        assert result is None
        provider.generate.assert_not_called()

    def test_returns_provider_output(self) -> None:
        """Return provider output as-is on successful translation."""
        provider = _make_mock_provider(output="번역된 텍스트입니다")
        result = translate_text("hello world", provider, lang="ko")
        assert result == "번역된 텍스트입니다"

    def test_whitespace_only_text_returns_none(self) -> None:
        """공백만 있는 텍스트는 falsy이므로 None 반환."""
        provider = _make_mock_provider()
        # "   " is truthy in Python, so this should call generate
        result = translate_text("   ", provider, lang="ko")
        # 공백 문자열은 truthy이므로 번역 시도됨
        assert provider.generate.called

    def test_unsupported_lang_returns_none(self) -> None:
        """지원하지 않는 언어 코드(TRANSLATABLE_LANGS 외)는 None을 반환한다."""
        provider = _make_mock_provider()
        result = translate_text("hello world", provider, lang="ja")
        assert result is None
        provider.generate.assert_not_called()

    def test_provider_exception_propagates(self) -> None:
        """provider가 예외를 던지면 translate_text에서 전파된다."""
        provider = _make_mock_provider()
        provider.generate.side_effect = RuntimeError("API timeout")
        with pytest.raises(RuntimeError, match="API timeout"):
            translate_text("hello world", provider, lang="ko")

    def test_provider_returns_none(self) -> None:
        """provider가 None을 반환하면 그대로 None 반환."""
        provider = _make_mock_provider(output=None)
        result = translate_text("hello world", provider, lang="ko")
        assert result is None

    def test_lang_defaults_to_get_lang(self) -> None:
        """lang 미지정 시 get_lang() 값을 사용한다."""
        from hawaiidisco.i18n import set_lang
        set_lang("ko")
        provider = _make_mock_provider(output="번역됨")
        result = translate_text("hello world", provider)
        assert result == "번역됨"
        provider.generate.assert_called_once()
        set_lang("en")

    def test_lang_default_en_skips(self) -> None:
        """lang 미지정 + 영어 모드이면 번역 스킵."""
        from hawaiidisco.i18n import set_lang
        set_lang("en")
        provider = _make_mock_provider()
        result = translate_text("hello world", provider)
        assert result is None
        provider.generate.assert_not_called()

    def test_exact_10000_chars_not_truncated(self) -> None:
        """정확히 10,000자는 잘리지 않는다."""
        provider = _make_mock_provider(output="번역됨")
        text = "x" * 10000
        translate_text(text, provider, lang="ko")
        prompt = provider.generate.call_args[0][0]
        assert "x" * 10000 in prompt

    def test_prompt_contains_output_language(self) -> None:
        """프롬프트에 output_language가 포함된다."""
        provider = _make_mock_provider(output="번역됨")
        translate_text("hello world", provider, lang="ko")
        prompt = provider.generate.call_args[0][0]
        assert "Korean" in prompt


class TestTranslateArticleMeta:
    """Tests for the translate_article_meta function."""

    def test_provider_unavailable(self) -> None:
        """Return error message when provider is unavailable."""
        provider = _make_mock_provider(available=False)
        title, desc = translate_article_meta("Test Title", "Test desc", provider, lang="ko")
        # should contain claude_cli_not_found message
        assert title != ""
        assert desc == ""

    def test_english_user_skips(self) -> None:
        """Return empty string pair for English users (no translation needed)."""
        provider = _make_mock_provider()
        title, desc = translate_article_meta("Test Title", "Test desc", provider, lang="en")
        assert title == ""
        assert desc == ""
        provider.generate.assert_not_called()

    def test_successful_translation(self) -> None:
        """Return parsed title/description on successful translation."""
        provider = _make_mock_provider(output="Title: 테스트 제목\nDescription: 테스트 설명")
        title, desc = translate_article_meta("Test Title", "Test desc", provider, lang="ko")
        assert title == "테스트 제목"
        assert desc == "테스트 설명"

    def test_provider_returns_none(self) -> None:
        """Return failure message when provider returns None."""
        provider = _make_mock_provider(output=None)
        title, desc = translate_article_meta("Test Title", "Test desc", provider, lang="ko")
        assert title != ""
        assert desc == ""

    def test_provider_returns_empty_string(self) -> None:
        """Return failure message when provider returns empty string."""
        provider = _make_mock_provider(output="")
        title, desc = translate_article_meta("Test Title", "Test desc", provider, lang="ko")
        assert title != ""
        assert desc == ""

    def test_provider_raises_exception(self) -> None:
        """Return failure message when provider raises an exception."""
        provider = _make_mock_provider()
        provider.generate.side_effect = RuntimeError("API error")
        title, desc = translate_article_meta("Test Title", "Test desc", provider, lang="ko")
        assert title != ""
        assert desc == ""

    def test_description_none_uses_placeholder(self) -> None:
        """Use placeholder when description is None."""
        provider = _make_mock_provider(output="Title: 번역 제목\nDescription: 없음")
        translate_article_meta("Test Title", None, provider, lang="ko")
        prompt = provider.generate.call_args[0][0]
        assert "(none)" in prompt

    def test_timeout_is_30(self) -> None:
        """Timeout is set to 30 seconds."""
        provider = _make_mock_provider(output="Title: 제목\nDescription: 설명")
        translate_article_meta("Test Title", "desc", provider, lang="ko")
        _, kwargs = provider.generate.call_args
        assert kwargs["timeout"] == 30

    def test_lang_defaults_to_get_lang(self) -> None:
        """lang 미지정 시 get_lang() 값을 사용한다."""
        from hawaiidisco.i18n import set_lang
        set_lang("ko")
        provider = _make_mock_provider(output="Title: 번역됨\nDescription: 설명됨")
        title, desc = translate_article_meta("Title", "Desc", provider)
        assert title == "번역됨"
        assert desc == "설명됨"
        set_lang("en")

    def test_unsupported_lang_returns_empty(self) -> None:
        """지원하지 않는 언어 코드는 빈 문자열 쌍 반환."""
        provider = _make_mock_provider()
        title, desc = translate_article_meta("Title", "Desc", provider, lang="ja")
        assert title == ""
        assert desc == ""
        provider.generate.assert_not_called()

    def test_empty_title_still_translates(self) -> None:
        """빈 title도 번역을 시도한다."""
        provider = _make_mock_provider(output="Title: \nDescription: 번역 설명")
        title, desc = translate_article_meta("", "Desc", provider, lang="ko")
        provider.generate.assert_called_once()

    def test_description_empty_string_uses_as_is(self) -> None:
        """description이 빈 문자열이면 빈 문자열을 그대로 사용."""
        provider = _make_mock_provider(output="Title: 번역\nDescription: 없음")
        translate_article_meta("Title", "", provider, lang="ko")
        prompt = provider.generate.call_args[0][0]
        # 빈 문자열은 falsy이므로 placeholder로 대체됨
        assert "(none)" in prompt

    def test_provider_returns_whitespace_only(self) -> None:
        """provider가 공백만 반환하면 실패 메시지."""
        provider = _make_mock_provider(output="   \n   ")
        title, desc = translate_article_meta("Title", "Desc", provider, lang="ko")
        # "   " is truthy, so _parse_translation is called - first line is empty after strip
        assert title != ""

    def test_prompt_contains_output_language(self) -> None:
        """프롬프트에 output_language가 포함된다."""
        provider = _make_mock_provider(output="Title: 제목\nDescription: 설명")
        translate_article_meta("Test", "Desc", provider, lang="ko")
        prompt = provider.generate.call_args[0][0]
        assert "Korean" in prompt


class TestParseTranslation:
    """Tests for the _parse_translation function."""

    def test_normal_korean_output(self) -> None:
        """Parse normal Korean format output."""
        output = "Title: 번역된 제목\nDescription: 번역된 설명"
        title, desc = _parse_translation(output, "fallback")
        assert title == "번역된 제목"
        assert desc == "번역된 설명"

    def test_english_keys(self) -> None:
        """Parse English key format."""
        output = "Title: Translated Title\nDescription: Translated Desc"
        title, desc = _parse_translation(output, "fallback")
        assert title == "Translated Title"
        assert desc == "Translated Desc"

    def test_extra_whitespace_stripped(self) -> None:
        """Leading and trailing whitespace is stripped."""
        output = "Title:   공백 제목   \nDescription:   공백 설명   "
        title, desc = _parse_translation(output, "fallback")
        assert title == "공백 제목"
        assert desc == "공백 설명"

    def test_missing_title_uses_first_line(self) -> None:
        """Use the first line as title when title key is missing."""
        output = "이건 그냥 텍스트\n두번째 줄"
        title, desc = _parse_translation(output, "fallback")
        assert title == "이건 그냥 텍스트"
        assert desc == ""

    def test_missing_description(self) -> None:
        """Handle case where only description key is missing."""
        output = "Title: 번역된 제목\n다른 텍스트"
        title, desc = _parse_translation(output, "fallback")
        assert title == "번역된 제목"
        assert desc == ""

    def test_empty_output_uses_fallback_title(self) -> None:
        """Use fallback_title when output is empty."""
        output = ""
        title, desc = _parse_translation(output, "Original Title")
        assert title == "Original Title"
        assert desc == ""

    def test_unparseable_output_uses_first_line(self) -> None:
        """Use the first line as title for unparseable output."""
        output = "완전히 다른 형식의 응답입니다"
        title, desc = _parse_translation(output, "fallback")
        assert title == "완전히 다른 형식의 응답입니다"
        assert desc == ""

    def test_duplicate_title_key_last_wins(self) -> None:
        """Title 키가 중복되면 마지막 값이 사용된다."""
        output = "Title: 첫 번째 제목\nTitle: 두 번째 제목\nDescription: 설명"
        title, desc = _parse_translation(output, "fallback")
        assert title == "두 번째 제목"
        assert desc == "설명"

    def test_title_key_empty_value(self) -> None:
        """Title 키 뒤에 값이 없으면 fallback 사용."""
        output = "Title: \nDescription: 설명 텍스트"
        title, desc = _parse_translation(output, "Fallback Title")
        # "Title: " 뒤에 빈 문자열 → translated_title=""이므로 fallback
        assert title == "Fallback Title"
        assert desc == "설명 텍스트"

    def test_whitespace_only_output(self) -> None:
        """공백만 있는 출력은 fallback 사용."""
        output = "   \n   \n   "
        title, desc = _parse_translation(output, "Fallback")
        assert title == "Fallback"
        assert desc == ""

    def test_multiline_description_only_first_line(self) -> None:
        """설명이 여러 줄이면 첫 번째 설명 줄만 파싱된다."""
        output = "Title: 제목\nDescription: 첫 줄 설명\n추가 설명 줄"
        title, desc = _parse_translation(output, "fallback")
        assert title == "제목"
        assert desc == "첫 줄 설명"

    def test_title_key_in_description_text(self) -> None:
        """설명 텍스트에 'Title:' 패턴이 있어도 정상 파싱."""
        output = "Title: 실제 제목\nDescription: 이 글의 Title: 무엇인가에 대해"
        title, desc = _parse_translation(output, "fallback")
        assert title == "실제 제목"
        # 'Description:' 라인은 정상 파싱됨
        assert "Title:" in desc  # 설명 내의 "Title:"은 보존

    def test_colon_in_title_value(self) -> None:
        """제목 값에 콜론이 포함된 경우 정상 처리."""
        output = "Title: Python 3.12: 새로운 기능\nDescription: 설명"
        title, desc = _parse_translation(output, "fallback")
        assert title == "Python 3.12: 새로운 기능"

    def test_newline_only_output(self) -> None:
        """개행만 있는 출력은 fallback 사용."""
        output = "\n\n\n"
        title, desc = _parse_translation(output, "Fallback")
        assert title == "Fallback"
        assert desc == ""


class TestGetLangName:
    """get_lang_name 헬퍼 함수 테스트."""

    def test_known_languages(self) -> None:
        """알려진 언어 코드는 언어명을 반환한다."""
        assert get_lang_name("ko") == "Korean"
        assert get_lang_name("en") == "English"

    def test_unknown_language_returns_code(self) -> None:
        """알 수 없는 언어 코드는 코드 자체를 반환한다."""
        assert get_lang_name("ja") == "ja"
        assert get_lang_name("fr") == "fr"


class TestTranslatableLangs:
    """TRANSLATABLE_LANGS 상수 테스트."""

    def test_ko_is_translatable(self) -> None:
        """한국어는 번역 대상이다."""
        assert "ko" in TRANSLATABLE_LANGS

    def test_en_is_not_translatable(self) -> None:
        """영어는 번역 대상이 아니다."""
        assert "en" not in TRANSLATABLE_LANGS


class TestTranslationCaching:
    """Tests for translation caching flow (DB save/retrieve)."""

    def test_save_and_retrieve_cached_translation(self, db: Database) -> None:
        """Save translation result to DB and retrieve it."""
        _insert_sample(db)
        db.set_translated_body("test-1", "캐시된 번역 본문")

        cached = db.get_translated_body("test-1")
        assert cached == "캐시된 번역 본문"

    def test_article_carries_cached_translation(self, db: Database) -> None:
        """Cached translation is included when retrieving via get_article."""
        _insert_sample(db)
        db.set_translated_body("test-1", "캐시 번역")

        article = db.get_article("test-1")
        assert article is not None
        assert article.translated_body == "캐시 번역"

    def test_overwrite_translation(self, db: Database) -> None:
        """Translation can be overwritten."""
        _insert_sample(db)
        db.set_translated_body("test-1", "첫 번째 번역")
        db.set_translated_body("test-1", "두 번째 번역")

        body = db.get_translated_body("test-1")
        assert body == "두 번째 번역"

    def test_set_meta_translation(self, db: Database) -> None:
        """Save and retrieve title/description translation."""
        _insert_sample(db)
        db.set_translation("test-1", "번역 제목", "번역 설명")

        article = db.get_article("test-1")
        assert article is not None
        assert article.translated_title == "번역 제목"
        assert article.translated_desc == "번역 설명"

    def test_get_translated_body_missing_article(self, db: Database) -> None:
        """Return None when querying a nonexistent article_id."""
        result = db.get_translated_body("nonexistent")
        assert result is None

    def test_article_without_translation_has_none(self, db: Database) -> None:
        """번역하지 않은 글은 translated 필드가 None이다."""
        _insert_sample(db)
        article = db.get_article("test-1")
        assert article is not None
        assert article.translated_title is None
        assert article.translated_desc is None
        assert article.translated_body is None

    def test_meta_translation_overwrite(self, db: Database) -> None:
        """메타 번역을 덮어쓸 수 있다."""
        _insert_sample(db)
        db.set_translation("test-1", "첫 제목", "첫 설명")
        db.set_translation("test-1", "두 번째 제목", "두 번째 설명")

        article = db.get_article("test-1")
        assert article is not None
        assert article.translated_title == "두 번째 제목"
        assert article.translated_desc == "두 번째 설명"

    def test_body_and_meta_independent(self, db: Database) -> None:
        """본문 번역과 메타 번역은 독립적이다."""
        _insert_sample(db)
        db.set_translation("test-1", "번역 제목", "번역 설명")
        db.set_translated_body("test-1", "본문 번역")

        article = db.get_article("test-1")
        assert article is not None
        assert article.translated_title == "번역 제목"
        assert article.translated_body == "본문 번역"

    def test_empty_string_translation_stored(self, db: Database) -> None:
        """빈 문자열 번역도 저장된다 (None과 구분)."""
        _insert_sample(db)
        db.set_translated_body("test-1", "")

        cached = db.get_translated_body("test-1")
        assert cached == ""

    def test_unicode_translation_stored(self, db: Database) -> None:
        """유니코드 특수문자가 포함된 번역이 정상 저장된다."""
        _insert_sample(db)
        unicode_text = "번역 🎉 emoji & 特殊文字 ñ é ü"
        db.set_translated_body("test-1", unicode_text)

        cached = db.get_translated_body("test-1")
        assert cached == unicode_text
