# Contributing Translations

Thank you for helping translate Hawaii Disco! This guide explains how to add a new language or improve an existing translation.

## How to Add a New Language

1. **Copy the English reference file:**
   ```bash
   cp hawaiidisco/i18n/locales/en.yml hawaiidisco/i18n/locales/{language_code}.yml
   ```
   Use the appropriate language code (e.g., `fr.yml` for French, `pt_BR.yml` for Brazilian Portuguese).

2. **Update the `meta` section:**
   ```yaml
   meta:
     language: "Fran\u00e7ais"   # Language name in its native form
     code: fr                 # Language code
     contributors:
       - name: Your Name
   ```

3. **Translate all string values.** Keep the keys in English:
   ```yaml
   # Good
   cancel: "Annuler"
   refreshing: "Actualisation..."

   # Bad - do NOT translate keys
   annuler: "Annuler"
   ```

4. **Preserve format placeholders** like `{count}`, `{title}`, `{name}`:
   ```yaml
   new_articles_found: "{count} nouveaux articles"
   bookmark_added: "\u2605 Ajout\u00e9 aux favoris : {title}"
   ```

5. **Register the language in `hawaiidisco/i18n/__init__.py`:**
   - Add a new member to the `Lang` enum
   - Add a locale mapping entry in `_LOCALE_MAP`

6. **Register the language in `hawaiidisco/ai/prompts.py`:**
   - Add the language name to `LANG_NAMES`
   - Add the language code to `TRANSLATABLE_LANGS` (if not English)

7. **Validate your translation:**
   ```bash
   python -m hawaiidisco.i18n.validate {language_code}
   ```
   This will report:
   - Missing keys (present in English but not in your file)
   - Empty values
   - Placeholder mismatches (e.g., `{count}` missing in translation)
   - Coverage percentage

8. **Submit a PR** with the title: `i18n: Add {Language} support`

## Improving Existing Translations

1. Edit the relevant `.yml` file in `hawaiidisco/i18n/locales/`
2. Run the validation script to check for issues
3. Add your name to the `meta.contributors` list
4. Submit a PR with the title: `i18n: Improve {Language} translations`

## Language Codes

| Language | Code | Filename |
|----------|------|----------|
| English | `en` | `en.yml` |
| Korean | `ko` | `ko.yml` |
| Japanese | `ja` | `ja.yml` |
| Chinese (Simplified) | `zh-CN` | `zh_CN.yml` |
| Spanish | `es` | `es.yml` |
| German | `de` | `de.yml` |

## Guidelines

- **Keep translations concise.** Terminal UIs have limited width; shorter is better.
- **Use natural phrasing.** Avoid word-by-word translation.
- **Keep technical terms in English** where appropriate (e.g., RSS, OPML, CLI).
- **Test in the app** if possible: set `language: {code}` in `~/.config/hawaiidisco/config.yml`.
- **Use `language: auto`** in config to test system locale detection.

## Config Example

```yaml
# ~/.config/hawaiidisco/config.yml
language: ja        # Japanese UI
# language: auto    # Auto-detect from system locale
```

## Questions?

Open an issue on GitHub if you have questions about the translation process.
