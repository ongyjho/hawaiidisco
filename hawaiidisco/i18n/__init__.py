"""Internationalization (i18n) support — YAML-based multilingual loader."""
from __future__ import annotations

import locale
import re
from enum import Enum
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Language enum — expanded for multilingual support
# ---------------------------------------------------------------------------

class Lang(Enum):
    EN = "en"
    KO = "ko"
    JA = "ja"
    ZH_CN = "zh-CN"
    ES = "es"
    DE = "de"


# Mapping from locale prefixes / aliases to Lang values for auto-detection.
_LOCALE_MAP: dict[str, Lang] = {
    "en": Lang.EN,
    "ko": Lang.KO,
    "ja": Lang.JA,
    "zh": Lang.ZH_CN,
    "zh_cn": Lang.ZH_CN,
    "zh_hans": Lang.ZH_CN,
    "es": Lang.ES,
    "de": Lang.DE,
}

# ---------------------------------------------------------------------------
# Internal state
# ---------------------------------------------------------------------------

_current_lang: Lang = Lang.EN

# Flat dict: {key: {Lang: template_string}}
_STRINGS: dict[str, dict[Lang, str]] = {}

# Locale YAML directory
_LOCALES_DIR: Path = Path(__file__).resolve().parent / "locales"

# Track which locales have been loaded
_loaded_locales: set[str] = set()

# ---------------------------------------------------------------------------
# YAML loader
# ---------------------------------------------------------------------------

def _lang_from_code(code: str) -> Lang | None:
    """Resolve a language code string to a Lang enum member."""
    # Direct match (e.g. "en", "ko")
    for member in Lang:
        if member.value == code:
            return member
    return None


def _yaml_filename(lang: Lang) -> str:
    """Return the YAML filename for a given Lang (e.g. zh-CN -> zh_CN.yml)."""
    return lang.value.replace("-", "_") + ".yml"


def _load_locale(lang: Lang) -> None:
    """Load a single locale YAML file and merge into *_STRINGS*."""
    code = lang.value
    if code in _loaded_locales:
        return

    path = _LOCALES_DIR / _yaml_filename(lang)
    if not path.exists():
        _loaded_locales.add(code)
        return

    with open(path, encoding="utf-8") as fh:
        raw: dict = yaml.safe_load(fh) or {}

    # Flatten: skip the "meta" section, merge everything else
    for key, value in raw.items():
        if key == "meta":
            continue
        if not isinstance(value, str):
            continue
        entry = _STRINGS.setdefault(key, {})
        entry[lang] = value

    _loaded_locales.add(code)


def _ensure_loaded(lang: Lang) -> None:
    """Ensure English (fallback) and the requested locale are loaded."""
    _load_locale(Lang.EN)
    if lang != Lang.EN:
        _load_locale(lang)


def load_all_locales() -> None:
    """Load every locale YAML found in the locales directory."""
    for member in Lang:
        _load_locale(member)

# ---------------------------------------------------------------------------
# Public API — fully backward-compatible
# ---------------------------------------------------------------------------

def set_lang(lang: str | None) -> None:
    """Set the current language.

    Accepts a language code string (e.g. ``"en"``, ``"ko"``, ``"ja"``,
    ``"zh-CN"``), ``"auto"`` for system locale detection, or *None* /
    invalid values which fall back to English.
    """
    global _current_lang

    if not lang:
        _current_lang = Lang.EN
        _ensure_loaded(_current_lang)
        return

    if lang == "auto":
        _current_lang = detect_system_lang()
        _ensure_loaded(_current_lang)
        return

    resolved = _lang_from_code(lang)
    if resolved is None:
        # Try normalising: zh_CN -> zh-CN, etc.
        normalised = lang.replace("_", "-")
        resolved = _lang_from_code(normalised)
    if resolved is None:
        resolved = Lang.EN

    _current_lang = resolved
    _ensure_loaded(_current_lang)


def get_lang() -> Lang:
    """Return the current language."""
    return _current_lang


def t(key: str, **kwargs: object) -> str:
    """Return the localised string for *key* in the current language.

    Falls back to English if the key has no translation for the active
    language, and returns *key* itself if no entry exists at all.
    """
    _ensure_loaded(_current_lang)

    entry = _STRINGS.get(key)
    if not entry:
        return key

    text = entry.get(_current_lang) or entry.get(Lang.EN, key)
    if kwargs:
        text = text.format(**kwargs)
    return text

# ---------------------------------------------------------------------------
# Auto-detection helper
# ---------------------------------------------------------------------------

def detect_system_lang() -> Lang:
    """Detect the best matching language from the system locale."""
    import os

    # Prefer explicit LANG / LC_ALL env vars, then fall back to locale.getlocale()
    loc = os.environ.get("LANG", os.environ.get("LC_ALL", ""))
    if not loc:
        try:
            loc = locale.getlocale()[0] or ""
        except ValueError:
            loc = ""

    # Normalise: en_US.UTF-8 -> en_us, zh_CN.UTF-8 -> zh_cn
    loc = loc.split(".")[0].lower()

    if not loc:
        return Lang.EN

    # Try full locale first (e.g. zh_cn -> ZH_CN)
    if loc in _LOCALE_MAP:
        return _LOCALE_MAP[loc]

    # Try just the language part (e.g. en, ko, ja, de, es)
    lang_prefix = loc.split("_")[0]
    return _LOCALE_MAP.get(lang_prefix, Lang.EN)

# ---------------------------------------------------------------------------
# Validation helpers (used by the validate CLI)
# ---------------------------------------------------------------------------

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def get_available_languages() -> list[str]:
    """Return a sorted list of language codes with locale YAML files."""
    codes: list[str] = []
    for member in Lang:
        path = _LOCALES_DIR / _yaml_filename(member)
        if path.exists():
            codes.append(member.value)
    return sorted(codes)


def validate_locale(lang_code: str) -> dict:
    """Validate a locale YAML against the English reference.

    Returns a dict with keys: ``missing``, ``extra``, ``empty``,
    ``placeholder_mismatch``, ``coverage_pct``.
    """
    load_all_locales()

    lang = _lang_from_code(lang_code)
    if lang is None:
        return {"error": f"Unknown language code: {lang_code}"}

    en_keys = {k for k, v in _STRINGS.items() if Lang.EN in v}
    lang_keys = {k for k, v in _STRINGS.items() if lang in v}

    missing = sorted(en_keys - lang_keys)
    extra = sorted(lang_keys - en_keys)
    empty: list[str] = []
    placeholder_mismatch: list[str] = []

    for key in sorted(en_keys & lang_keys):
        en_text = _STRINGS[key].get(Lang.EN, "")
        lang_text = _STRINGS[key].get(lang, "")

        if not lang_text:
            empty.append(key)
            continue

        en_ph = set(_PLACEHOLDER_RE.findall(en_text))
        lang_ph = set(_PLACEHOLDER_RE.findall(lang_text))
        if en_ph != lang_ph:
            placeholder_mismatch.append(key)

    total = len(en_keys)
    translated = total - len(missing) - len(empty)
    coverage = round(translated / total * 100, 1) if total else 100.0

    return {
        "missing": missing,
        "extra": extra,
        "empty": empty,
        "placeholder_mismatch": placeholder_mismatch,
        "coverage_pct": coverage,
    }
