"""Tests for i18n multilingual support."""
from __future__ import annotations

from hawaiidisco.i18n import Lang, get_lang, set_lang, t


class TestSetLang:
    """Tests for set_lang / get_lang."""

    def test_default_is_english(self) -> None:
        """Default language is English."""
        set_lang("en")
        assert get_lang() == Lang.EN

    def test_set_korean(self) -> None:
        """Switch language to Korean."""
        set_lang("ko")
        assert get_lang() == Lang.KO
        set_lang("en")  # restore

    def test_invalid_lang_falls_back_to_en(self) -> None:
        """Invalid language code falls back to English."""
        set_lang("xx")
        assert get_lang() == Lang.EN


class TestTranslation:
    """Tests for the t() translation function."""

    def test_english_string(self) -> None:
        """Return English string in English mode."""
        set_lang("en")
        assert t("quit") == "Quit"

    def test_korean_string(self) -> None:
        """Return Korean string in Korean mode."""
        set_lang("ko")
        assert t("quit") == "종료"
        set_lang("en")

    def test_format_kwargs(self) -> None:
        """Format kwargs are correctly substituted."""
        set_lang("en")
        result = t("new_articles_found", count=5)
        assert "5" in result

    def test_format_kwargs_korean(self) -> None:
        """Format kwargs are substituted in Korean mode as well."""
        set_lang("ko")
        result = t("new_articles_found", count=3)
        assert "3" in result
        set_lang("en")

    def test_missing_key_returns_key(self) -> None:
        """Missing key returns the key itself."""
        set_lang("en")
        assert t("nonexistent_key_xyz") == "nonexistent_key_xyz"

    def test_lang_switch_changes_output(self) -> None:
        """Switching language changes the output."""
        set_lang("en")
        en_text = t("refreshing")
        set_lang("ko")
        ko_text = t("refreshing")
        assert en_text != ko_text
        assert en_text == "Refreshing..."
        assert ko_text == "새로고침 중..."
        set_lang("en")


class TestTranslationEdgeCases:
    """t() 함수 엣지케이스 테스트."""

    def test_missing_kwargs_leaves_placeholder(self) -> None:
        """필요한 kwargs가 누락되면 placeholder가 그대로 남는다 (format 미호출)."""
        set_lang("en")
        result = t("new_articles_found")
        # kwargs가 없으면 format()을 호출하지 않으므로 {count}가 그대로 남음
        assert "{count}" in result

    def test_extra_kwargs_ignored(self) -> None:
        """불필요한 kwargs는 무시된다."""
        set_lang("en")
        result = t("new_articles_found", count=5, extra="ignored")
        assert "5" in result

    def test_missing_key_with_kwargs(self) -> None:
        """존재하지 않는 키에 kwargs를 전달해도 키 자체를 반환한다."""
        set_lang("en")
        result = t("nonexistent_key", count=5)
        assert result == "nonexistent_key"

    def test_empty_string_key(self) -> None:
        """빈 문자열 키는 키 자체를 반환한다."""
        set_lang("en")
        assert t("") == ""

    def test_korean_fallback_to_english(self) -> None:
        """한국어가 없는 키는 영어로 폴백한다 (수동 검증용)."""
        from hawaiidisco.i18n import _STRINGS
        # 모든 기존 키가 양쪽 다 있으므로 임시로 한쪽만 있는 키 추가 후 복원
        _STRINGS["_test_en_only"] = {Lang.EN: "English only"}
        set_lang("ko")
        result = t("_test_en_only")
        assert result == "English only"
        del _STRINGS["_test_en_only"]
        set_lang("en")

    def test_all_format_keys_produce_valid_output(self) -> None:
        """format 인자가 필요한 모든 키가 올바르게 치환된다."""
        # format 인자가 필요한 키와 인자 매핑
        format_keys = {
            "new_articles_found": {"count": 10},
            "bookmark_added": {"title": "Test"},
            "bookmark_removed": {"title": "Test"},
            "searching": {"query": "test"},
            "feed_added": {"name": "TestFeed"},
            "last_refresh": {"time": "12:00"},
            "minutes_ago": {"n": 5},
            "hours_ago": {"n": 3},
            "days_ago": {"n": 2},
            "fetch_error": {"error": "timeout"},
            "translated_preview": {"title": "test"},
            "article_count": {"count": 42},
        }
        for lang_code in ("en", "ko"):
            set_lang(lang_code)
            for key, kwargs in format_keys.items():
                result = t(key, **kwargs)
                assert result, f"'{key}' ({lang_code}) 빈 문자열 반환"
                # format placeholder가 남아있지 않은지 확인
                assert "{" not in result, f"'{key}' ({lang_code}) 미치환 placeholder: {result}"
        set_lang("en")

    def test_set_lang_empty_string(self) -> None:
        """빈 문자열로 set_lang 호출 시 EN으로 폴백."""
        set_lang("")
        assert get_lang() == Lang.EN

    def test_set_lang_none_falls_back_to_en(self) -> None:
        """None 전달 시 ValueError가 내부에서 잡혀 EN으로 폴백한다."""
        set_lang(None)  # type: ignore[arg-type]
        assert get_lang() == Lang.EN


class TestAllKeysHaveBothLanguages:
    """Verify all keys have both English and Korean translations."""

    def test_all_keys_have_en_and_ko(self) -> None:
        """Every string key includes both EN and KO languages."""
        from hawaiidisco.i18n import _STRINGS
        for key, entry in _STRINGS.items():
            assert Lang.EN in entry, f"'{key}' missing EN"
            assert Lang.KO in entry, f"'{key}' missing KO"

    def test_no_empty_translation_values(self) -> None:
        """번역 값이 빈 문자열이 아닌지 확인한다."""
        from hawaiidisco.i18n import _STRINGS
        for key, entry in _STRINGS.items():
            for lang, text in entry.items():
                assert text, f"'{key}' ({lang.value}) 빈 번역 값"

    def test_format_placeholders_consistent(self) -> None:
        """EN/KO 번역이 동일한 format placeholder를 사용한다."""
        import re
        from hawaiidisco.i18n import _STRINGS
        placeholder_re = re.compile(r"\{(\w+)\}")
        for key, entry in _STRINGS.items():
            en_placeholders = set(placeholder_re.findall(entry.get(Lang.EN, "")))
            ko_placeholders = set(placeholder_re.findall(entry.get(Lang.KO, "")))
            assert en_placeholders == ko_placeholders, (
                f"'{key}' placeholder 불일치: EN={en_placeholders}, KO={ko_placeholders}"
            )
