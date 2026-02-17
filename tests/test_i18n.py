"""Tests for i18n multilingual support."""
from __future__ import annotations

import re

from hawaiidisco.i18n import (
    Lang,
    _STRINGS,
    get_available_languages,
    get_lang,
    load_all_locales,
    set_lang,
    t,
    validate_locale,
)


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

    def test_set_japanese(self) -> None:
        """Switch language to Japanese."""
        set_lang("ja")
        assert get_lang() == Lang.JA
        set_lang("en")

    def test_set_chinese(self) -> None:
        """Switch language to Simplified Chinese."""
        set_lang("zh-CN")
        assert get_lang() == Lang.ZH_CN
        set_lang("en")

    def test_set_spanish(self) -> None:
        """Switch language to Spanish."""
        set_lang("es")
        assert get_lang() == Lang.ES
        set_lang("en")

    def test_set_german(self) -> None:
        """Switch language to German."""
        set_lang("de")
        assert get_lang() == Lang.DE
        set_lang("en")

    def test_invalid_lang_falls_back_to_en(self) -> None:
        """Invalid language code falls back to English."""
        set_lang("xx")
        assert get_lang() == Lang.EN

    def test_set_lang_empty_string(self) -> None:
        """Empty string falls back to EN."""
        set_lang("")
        assert get_lang() == Lang.EN

    def test_set_lang_none_falls_back_to_en(self) -> None:
        """None falls back to EN."""
        set_lang(None)  # type: ignore[arg-type]
        assert get_lang() == Lang.EN

    def test_auto_detection(self) -> None:
        """'auto' triggers system locale detection without crashing."""
        set_lang("auto")
        assert isinstance(get_lang(), Lang)
        set_lang("en")


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

    def test_japanese_string(self) -> None:
        """Return Japanese string in Japanese mode."""
        set_lang("ja")
        assert t("quit") == "終了"
        set_lang("en")

    def test_chinese_string(self) -> None:
        """Return Chinese string in Chinese mode."""
        set_lang("zh-CN")
        assert t("quit") == "退出"
        set_lang("en")

    def test_spanish_string(self) -> None:
        """Return Spanish string in Spanish mode."""
        set_lang("es")
        assert t("quit") == "Salir"
        set_lang("en")

    def test_german_string(self) -> None:
        """Return German string in German mode."""
        set_lang("de")
        assert t("quit") == "Beenden"
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

    def test_format_kwargs_japanese(self) -> None:
        """Format kwargs work in Japanese."""
        set_lang("ja")
        result = t("new_articles_found", count=7)
        assert "7" in result
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
    """t() edge-case tests."""

    def test_missing_kwargs_leaves_placeholder(self) -> None:
        """Missing kwargs leave the placeholder intact."""
        set_lang("en")
        result = t("new_articles_found")
        assert "{count}" in result

    def test_extra_kwargs_ignored(self) -> None:
        """Extra kwargs are silently ignored."""
        set_lang("en")
        result = t("new_articles_found", count=5, extra="ignored")
        assert "5" in result

    def test_missing_key_with_kwargs(self) -> None:
        """Non-existent key with kwargs returns the key."""
        set_lang("en")
        result = t("nonexistent_key", count=5)
        assert result == "nonexistent_key"

    def test_empty_string_key(self) -> None:
        """Empty string key returns empty string."""
        set_lang("en")
        assert t("") == ""

    def test_fallback_to_english(self) -> None:
        """A key missing in the current language falls back to English."""
        # Inject a temporary entry with only EN
        _STRINGS["_test_en_only"] = {Lang.EN: "English only"}
        set_lang("ko")
        result = t("_test_en_only")
        assert result == "English only"
        del _STRINGS["_test_en_only"]
        set_lang("en")

    def test_all_format_keys_produce_valid_output(self) -> None:
        """All keys with format placeholders produce valid output in every language."""
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
        load_all_locales()
        for lang in Lang:
            set_lang(lang.value)
            for key, kwargs in format_keys.items():
                result = t(key, **kwargs)
                assert result, f"'{key}' ({lang.value}) empty result"
                assert "{" not in result, (
                    f"'{key}' ({lang.value}) unsubstituted placeholder: {result}"
                )
        set_lang("en")


class TestAllKeysConsistency:
    """Verify all locales have consistent keys and translations."""

    def test_all_keys_have_en(self) -> None:
        """Every key includes an English translation."""
        load_all_locales()
        for key, entry in _STRINGS.items():
            assert Lang.EN in entry, f"'{key}' missing EN"

    def test_en_ko_complete(self) -> None:
        """EN and KO both have all keys (P0 languages)."""
        load_all_locales()
        for key, entry in _STRINGS.items():
            assert Lang.EN in entry, f"'{key}' missing EN"
            assert Lang.KO in entry, f"'{key}' missing KO"

    def test_no_empty_translation_values(self) -> None:
        """No translation values are empty strings."""
        load_all_locales()
        for key, entry in _STRINGS.items():
            for lang, text in entry.items():
                assert text, f"'{key}' ({lang.value}) empty value"

    def test_format_placeholders_consistent(self) -> None:
        """All languages use the same format placeholders as English."""
        load_all_locales()
        placeholder_re = re.compile(r"\{(\w+)\}")
        for key, entry in _STRINGS.items():
            en_text = entry.get(Lang.EN, "")
            en_placeholders = set(placeholder_re.findall(en_text))
            for lang, text in entry.items():
                if lang == Lang.EN:
                    continue
                lang_placeholders = set(placeholder_re.findall(text))
                assert en_placeholders == lang_placeholders, (
                    f"'{key}' placeholder mismatch: "
                    f"EN={en_placeholders}, {lang.value}={lang_placeholders}"
                )


class TestValidation:
    """Tests for the validate_locale helper."""

    def test_validate_en(self) -> None:
        """English should have 100% coverage."""
        result = validate_locale("en")
        assert result["coverage_pct"] == 100.0
        assert result["missing"] == []

    def test_validate_ko(self) -> None:
        """Korean should have 100% coverage."""
        result = validate_locale("ko")
        assert result["coverage_pct"] == 100.0
        assert result["missing"] == []

    def test_validate_ja(self) -> None:
        """Japanese should have 100% coverage."""
        result = validate_locale("ja")
        assert result["coverage_pct"] == 100.0

    def test_validate_zh_cn(self) -> None:
        """Chinese should have 100% coverage."""
        result = validate_locale("zh-CN")
        assert result["coverage_pct"] == 100.0

    def test_validate_es(self) -> None:
        """Spanish should have 100% coverage."""
        result = validate_locale("es")
        assert result["coverage_pct"] == 100.0

    def test_validate_de(self) -> None:
        """German should have 100% coverage."""
        result = validate_locale("de")
        assert result["coverage_pct"] == 100.0

    def test_validate_unknown_code(self) -> None:
        """Unknown language code returns error."""
        result = validate_locale("xx")
        assert "error" in result

    def test_no_placeholder_mismatches(self) -> None:
        """No locale has placeholder mismatches."""
        for code in get_available_languages():
            result = validate_locale(code)
            if "error" in result:
                continue
            assert result["placeholder_mismatch"] == [], (
                f"{code} has placeholder mismatches: {result['placeholder_mismatch']}"
            )


class TestAvailableLanguages:
    """Tests for get_available_languages."""

    def test_includes_core_languages(self) -> None:
        """Available languages include all 6 supported languages."""
        langs = get_available_languages()
        assert "en" in langs
        assert "ko" in langs
        assert "ja" in langs
        assert "zh-CN" in langs
        assert "es" in langs
        assert "de" in langs

    def test_returns_sorted(self) -> None:
        """Results are sorted."""
        langs = get_available_languages()
        assert langs == sorted(langs)
