"""Tests for configuration loading."""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from hawaiidisco.config import load_config, _resolve_env, _prompt_yn, remove_feed, setup_obsidian
from hawaiidisco.i18n import get_lang, Lang


@pytest.fixture()
def config_file(tmp_path: Path) -> Path:
    """Return a temporary config.yml path."""
    return tmp_path / "config.yml"


class TestLoadConfig:
    """Tests for the load_config function."""

    def test_default_language_is_en(self, config_file: Path) -> None:
        """Default language is 'en' when not specified."""
        config_file.write_text("feeds: []\n", encoding="utf-8")
        config = load_config(config_file)
        assert config.language == "en"

    def test_language_ko(self, config_file: Path) -> None:
        """Korean language setting is loaded with language: ko."""
        config_file.write_text("language: ko\nfeeds: []\n", encoding="utf-8")
        config = load_config(config_file)
        assert config.language == "ko"
        assert get_lang() == Lang.KO
        # restore
        from hawaiidisco.i18n import set_lang
        set_lang("en")

    def test_ai_config_defaults(self, config_file: Path) -> None:
        """Use default values when AI config is absent."""
        config_file.write_text("feeds: []\n", encoding="utf-8")
        config = load_config(config_file)
        assert config.ai.provider == "claude_cli"
        assert config.ai.api_key == ""
        assert config.ai.model == ""

    def test_ai_config_custom(self, config_file: Path) -> None:
        """Load custom AI configuration."""
        data = {
            "ai": {
                "provider": "anthropic",
                "api_key": "sk-test-123",
                "model": "claude-3-opus",
            },
            "feeds": [],
        }
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        config = load_config(config_file)
        assert config.ai.provider == "anthropic"
        assert config.ai.api_key == "sk-test-123"
        assert config.ai.model == "claude-3-opus"

    def test_feeds_loading(self, config_file: Path) -> None:
        """Feed list is loaded correctly."""
        data = {
            "feeds": [
                {"url": "https://example.com/feed", "name": "Test"},
            ],
        }
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        config = load_config(config_file)
        assert len(config.feeds) == 1
        assert config.feeds[0].url == "https://example.com/feed"
        assert config.feeds[0].name == "Test"

    def test_missing_file_uses_defaults(self, tmp_path: Path) -> None:
        """Use defaults when the config file is missing."""
        config = load_config(tmp_path / "nonexistent.yml")
        assert config.language == "en"
        assert config.feeds == []
        assert config.refresh_interval == 30


class TestThemeConfig:
    """Tests for theme configuration."""

    def test_default_theme(self, config_file: Path) -> None:
        """Default theme is textual-dark."""
        config_file.write_text("feeds: []\n", encoding="utf-8")
        config = load_config(config_file)
        assert config.theme == "textual-dark"

    def test_custom_theme(self, config_file: Path) -> None:
        """Custom theme can be loaded."""
        data = {"theme": "nord", "feeds": []}
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        config = load_config(config_file)
        assert config.theme == "nord"

    def test_theme_from_full_config(self, config_file: Path) -> None:
        """Theme can be read from full config."""
        data = {
            "language": "ko",
            "theme": "dracula",
            "feeds": [],
            "refresh_interval": 15,
        }
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        config = load_config(config_file)
        assert config.theme == "dracula"
        assert config.language == "ko"
        assert config.refresh_interval == 15
        # restore
        from hawaiidisco.i18n import set_lang
        set_lang("en")


class TestResolveEnv:
    """Tests for _resolve_env environment variable substitution."""

    def test_env_var_substitution(self, monkeypatch) -> None:
        """${ENV_VAR} pattern is substituted with environment variable value."""
        monkeypatch.setenv("TEST_API_KEY", "my-secret-key")
        assert _resolve_env("${TEST_API_KEY}") == "my-secret-key"

    def test_missing_env_var_returns_empty(self) -> None:
        """Missing environment variable returns empty string."""
        assert _resolve_env("${NONEXISTENT_VAR_XYZ}") == ""

    def test_plain_string_unchanged(self) -> None:
        """Plain string is returned unchanged."""
        assert _resolve_env("sk-test-123") == "sk-test-123"

    def test_empty_string_unchanged(self) -> None:
        """Empty string is returned unchanged."""
        assert _resolve_env("") == ""

    def test_env_var_in_config(self, config_file: Path, monkeypatch) -> None:
        """Load API key from config.yml using ${ENV_VAR} pattern."""
        monkeypatch.setenv("MY_API_KEY", "resolved-key")
        data = {
            "ai": {
                "provider": "anthropic",
                "api_key": "${MY_API_KEY}",
            },
            "feeds": [],
        }
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        config = load_config(config_file)
        assert config.ai.api_key == "resolved-key"


class TestObsidianConfig:
    """Tests for Obsidian configuration loading."""

    def test_default_obsidian_disabled(self, config_file: Path) -> None:
        """Obsidian is disabled by default when not in config."""
        config_file.write_text("feeds: []\n", encoding="utf-8")
        config = load_config(config_file)
        assert config.obsidian.enabled is False
        assert config.obsidian.vault_path == Path("")

    def test_obsidian_config_loading(self, config_file: Path) -> None:
        """Full obsidian config is parsed correctly."""
        data = {
            "feeds": [],
            "obsidian": {
                "enabled": True,
                "vault_path": "/tmp/test-vault",
                "folder": "my-notes",
                "template": "minimal",
                "auto_save": False,
                "include_insight": False,
                "include_translation": True,
                "tags_prefix": "hd",
            },
        }
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        config = load_config(config_file)
        assert config.obsidian.enabled is True
        assert config.obsidian.vault_path == Path("/tmp/test-vault")
        assert config.obsidian.folder == "my-notes"
        assert config.obsidian.template == "minimal"
        assert config.obsidian.auto_save is False
        assert config.obsidian.include_insight is False
        assert config.obsidian.include_translation is True
        assert config.obsidian.tags_prefix == "hd"

    def test_obsidian_vault_path_expanduser(self, config_file: Path) -> None:
        """vault_path with ~ is expanded."""
        data = {
            "feeds": [],
            "obsidian": {
                "enabled": True,
                "vault_path": "~/Documents/Vault",
            },
        }
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        config = load_config(config_file)
        assert "~" not in str(config.obsidian.vault_path)

    def test_obsidian_defaults_when_partial(self, config_file: Path) -> None:
        """Missing obsidian fields use defaults."""
        data = {
            "feeds": [],
            "obsidian": {
                "enabled": True,
                "vault_path": "/tmp/vault",
            },
        }
        config_file.write_text(yaml.dump(data), encoding="utf-8")
        config = load_config(config_file)
        assert config.obsidian.folder == "hawaii-disco"
        assert config.obsidian.auto_save is True
        assert config.obsidian.tags_prefix == "hawaiidisco"


class TestRemoveFeed:
    """Tests for the remove_feed function."""

    def test_remove_existing_feed(self, tmp_path: Path, monkeypatch) -> None:
        """Removing an existing feed returns True."""
        config_path = tmp_path / "config.yml"
        data = {
            "feeds": [
                {"url": "https://a.com/feed", "name": "Feed A"},
                {"url": "https://b.com/feed", "name": "Feed B"},
            ]
        }
        config_path.write_text(yaml.dump(data), encoding="utf-8")
        monkeypatch.setattr("hawaiidisco.config.CONFIG_PATH", config_path)

        result = remove_feed("https://a.com/feed")
        assert result is True

        # Verify the feed was removed from the file
        with open(config_path, encoding="utf-8") as f:
            updated = yaml.safe_load(f)
        assert len(updated["feeds"]) == 1
        assert updated["feeds"][0]["url"] == "https://b.com/feed"

    def test_remove_nonexistent_feed(self, tmp_path: Path, monkeypatch) -> None:
        """Removing a non-existent feed returns False."""
        config_path = tmp_path / "config.yml"
        data = {"feeds": [{"url": "https://a.com/feed", "name": "Feed A"}]}
        config_path.write_text(yaml.dump(data), encoding="utf-8")
        monkeypatch.setattr("hawaiidisco.config.CONFIG_PATH", config_path)

        result = remove_feed("https://nonexistent.com/feed")
        assert result is False


class TestPromptYn:
    """Tests for the _prompt_yn helper."""

    def test_default_true_empty_input(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        assert _prompt_yn("test", default=True) is True

    def test_default_false_empty_input(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda prompt="": "")
        assert _prompt_yn("test", default=False) is False

    def test_yes_input(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda prompt="": "y")
        assert _prompt_yn("test", default=False) is True

    def test_no_input(self, monkeypatch) -> None:
        monkeypatch.setattr("builtins.input", lambda prompt="": "n")
        assert _prompt_yn("test", default=True) is False


class TestSetupObsidian:
    """Tests for the interactive Obsidian setup wizard."""

    def test_creates_config(self, tmp_path: Path, monkeypatch) -> None:
        """setup_obsidian writes obsidian section to config.yml."""
        config_path = tmp_path / "config.yml"
        config_path.write_text("language: en\nfeeds: []\n", encoding="utf-8")
        monkeypatch.setattr("hawaiidisco.config.CONFIG_PATH", config_path)

        vault = tmp_path / "my-vault"
        vault.mkdir()

        # vault_path, folder(default), auto_save(Y), insight(Y), translation(Y), tags(default)
        inputs = iter([str(vault), "", "", "", "", ""])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        setup_obsidian()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["obsidian"]["enabled"] is True
        assert data["obsidian"]["vault_path"] == str(vault)
        assert data["obsidian"]["folder"] == "hawaii-disco"
        assert data["obsidian"]["auto_save"] is True

    def test_invalid_path_retries(self, tmp_path: Path, monkeypatch) -> None:
        """setup_obsidian retries when vault path does not exist."""
        config_path = tmp_path / "config.yml"
        config_path.write_text("feeds: []\n", encoding="utf-8")
        monkeypatch.setattr("hawaiidisco.config.CONFIG_PATH", config_path)

        vault = tmp_path / "real-vault"
        vault.mkdir()

        # First input is invalid, second is valid
        inputs = iter(["/nonexistent/path", str(vault), "", "", "", "", ""])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        setup_obsidian()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["obsidian"]["enabled"] is True
        assert data["obsidian"]["vault_path"] == str(vault)

    def test_preserves_existing_config(self, tmp_path: Path, monkeypatch) -> None:
        """setup_obsidian preserves other config sections."""
        config_path = tmp_path / "config.yml"
        config_path.write_text(
            "language: ko\nfeeds:\n- url: https://example.com\n  name: Test\n",
            encoding="utf-8",
        )
        monkeypatch.setattr("hawaiidisco.config.CONFIG_PATH", config_path)

        vault = tmp_path / "vault"
        vault.mkdir()

        inputs = iter([str(vault), "", "", "", "", ""])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        setup_obsidian()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["language"] == "ko"
        assert len(data["feeds"]) == 1
        assert data["obsidian"]["enabled"] is True

        # restore
        from hawaiidisco.i18n import set_lang
        set_lang("en")

    def test_custom_values(self, tmp_path: Path, monkeypatch) -> None:
        """setup_obsidian saves custom user inputs."""
        config_path = tmp_path / "config.yml"
        config_path.write_text("feeds: []\n", encoding="utf-8")
        monkeypatch.setattr("hawaiidisco.config.CONFIG_PATH", config_path)

        vault = tmp_path / "vault"
        vault.mkdir()

        # vault, folder=notes, auto_save=n, insight=n, translation=y, tags=hd
        inputs = iter([str(vault), "notes", "n", "n", "y", "hd"])
        monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

        setup_obsidian()

        with open(config_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["obsidian"]["folder"] == "notes"
        assert data["obsidian"]["auto_save"] is False
        assert data["obsidian"]["include_insight"] is False
        assert data["obsidian"]["include_translation"] is True
        assert data["obsidian"]["tags_prefix"] == "hd"
