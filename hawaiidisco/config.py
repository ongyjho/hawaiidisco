"""Load configuration from YAML."""
from __future__ import annotations

import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from hawaiidisco.i18n import set_lang


CONFIG_PATH = Path("~/.config/hawaiidisco/config.yml").expanduser()
# Seed config bundled with the package (for development)
_PACKAGE_DIR = Path(__file__).resolve().parent.parent
_SEED_CONFIG = _PACKAGE_DIR / "config.example.yml"


@dataclass
class FeedConfig:
    url: str
    name: str


@dataclass
class AIConfig:
    provider: str = "claude_cli"  # claude_cli | anthropic | openai
    api_key: str = ""
    model: str = ""


@dataclass
class InsightConfig:
    enabled: bool = True
    mode: str = "manual"  # auto | manual


@dataclass
class DigestConfig:
    enabled: bool = True
    period_days: int = 7
    max_articles: int = 20
    bookmarked_only: bool = False
    save_to_obsidian: bool = True


@dataclass
class ObsidianConfig:
    enabled: bool = False
    vault_path: Path = field(default_factory=lambda: Path(""))
    folder: str = "hawaii-disco"
    template: str = "default"  # default | minimal
    auto_save: bool = True
    include_insight: bool = True
    include_translation: bool = True
    tags_prefix: str = "hawaiidisco"


@dataclass
class Config:
    language: str = "en"
    theme: str = "textual-dark"
    ai: AIConfig = field(default_factory=AIConfig)
    feeds: list[FeedConfig] = field(default_factory=list)
    refresh_interval: int = 30
    insight: InsightConfig = field(default_factory=InsightConfig)
    bookmark_dir: Path = Path("~/.local/share/hawaiidisco/bookmarks")
    db_path: Path = Path("~/.local/share/hawaiidisco/hawaiidisco.db")
    allow_insecure_ssl: bool = False
    obsidian: ObsidianConfig = field(default_factory=ObsidianConfig)
    digest: DigestConfig = field(default_factory=DigestConfig)


def _resolve_env(value: str) -> str:
    """Resolve ``${ENV_VAR}`` patterns by substituting environment variable values."""
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        return os.environ.get(env_name, "")
    return value


def _ensure_config() -> None:
    """Copy seed config to user config path if it does not exist."""
    if CONFIG_PATH.exists():
        return
    if _SEED_CONFIG.exists():
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(_SEED_CONFIG, CONFIG_PATH)


def load_config(path: Path | None = None) -> Config:
    """Load configuration from a YAML file. Use defaults if the file is missing."""
    _ensure_config()
    config_path = path or CONFIG_PATH

    raw: dict = {}
    if config_path.exists():
        with open(config_path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    language = raw.get("language", "en")
    set_lang(language)

    # AI configuration
    ai_raw = raw.get("ai", {})
    api_key = _resolve_env(ai_raw.get("api_key", ""))
    ai = AIConfig(
        provider=ai_raw.get("provider", "claude_cli"),
        api_key=api_key,
        model=ai_raw.get("model", ""),
    )

    feeds = [
        FeedConfig(url=feed["url"], name=feed.get("name", feed["url"]))
        for feed in raw.get("feeds", [])
    ]

    insight_raw = raw.get("insight", {})
    insight = InsightConfig(
        enabled=insight_raw.get("enabled", True),
        mode=insight_raw.get("mode", "manual"),
    )

    bookmark_dir = Path(
        os.path.expanduser(raw.get("bookmark_dir", "~/.local/share/hawaiidisco/bookmarks"))
    )

    # Obsidian configuration
    obs_raw = raw.get("obsidian", {})
    obs_vault_str = obs_raw.get("vault_path", "")
    obs_vault = Path(os.path.expanduser(obs_vault_str)) if obs_vault_str else Path("")
    obsidian = ObsidianConfig(
        enabled=obs_raw.get("enabled", False),
        vault_path=obs_vault,
        folder=obs_raw.get("folder", "hawaii-disco"),
        template=obs_raw.get("template", "default"),
        auto_save=obs_raw.get("auto_save", True),
        include_insight=obs_raw.get("include_insight", True),
        include_translation=obs_raw.get("include_translation", True),
        tags_prefix=obs_raw.get("tags_prefix", "hawaiidisco"),
    )

    # Digest configuration
    dig_raw = raw.get("digest", {})
    digest = DigestConfig(
        enabled=dig_raw.get("enabled", True),
        period_days=dig_raw.get("period_days", 7),
        max_articles=dig_raw.get("max_articles", 20),
        bookmarked_only=dig_raw.get("bookmarked_only", False),
        save_to_obsidian=dig_raw.get("save_to_obsidian", True),
    )

    config = Config(
        language=language,
        theme=raw.get("theme", "textual-dark"),
        ai=ai,
        feeds=feeds,
        refresh_interval=raw.get("refresh_interval", 30),
        insight=insight,
        bookmark_dir=bookmark_dir,
        db_path=Path("~/.local/share/hawaiidisco/hawaiidisco.db").expanduser(),
        allow_insecure_ssl=raw.get("allow_insecure_ssl", False),
        obsidian=obsidian,
        digest=digest,
    )
    return config


def add_feed(feed: FeedConfig) -> None:
    """Add a feed entry to config.yml."""
    _ensure_config()

    raw: dict = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    feeds = raw.get("feeds", [])
    # Skip duplicate URLs
    if any(f["url"] == feed.url for f in feeds):
        return
    feeds.append({"url": feed.url, "name": feed.name})
    raw["feeds"] = feeds

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def remove_feed(feed_url: str) -> bool:
    """Remove a feed entry from config.yml by URL. Return True if removed."""
    _ensure_config()

    raw: dict = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    feeds = raw.get("feeds", [])
    original_len = len(feeds)
    feeds = [f for f in feeds if f["url"] != feed_url]
    if len(feeds) == original_len:
        return False

    raw["feeds"] = feeds
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(raw, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    return True


def ensure_dirs(config: Config) -> None:
    """Create required directories if they do not exist. 소유자만 접근 가능하도록 권한 설정."""
    dirs: list[Path] = [config.db_path.parent, config.bookmark_dir]
    if config.obsidian.enabled and config.obsidian.vault_path != Path(""):
        dirs.append(config.obsidian.vault_path / config.obsidian.folder)
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True, mode=0o700)
        # 기존 디렉토리도 권한 보정
        d.chmod(0o700)
