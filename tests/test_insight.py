"""Tests for insight generation with persona support."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import yaml
from pathlib import Path

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.config import load_config
from hawaiidisco.db import Article
from hawaiidisco.insight import generate_insight, get_or_generate_insight


def _make_article(**kwargs) -> Article:
    defaults = {
        "id": "abc123",
        "feed_name": "TestFeed",
        "title": "New AI Framework Released",
        "link": "https://example.com/article",
        "description": "A new framework for building AI apps.",
        "published_at": datetime(2025, 1, 1),
        "fetched_at": datetime(2025, 1, 1),
        "is_read": False,
        "is_bookmarked": False,
        "insight": None,
    }
    defaults.update(kwargs)
    return Article(**defaults)


def _make_provider(response: str = "Great insight") -> MagicMock:
    provider = MagicMock(spec=AIProvider)
    provider.name = "mock"
    provider.is_available.return_value = True
    provider.generate.return_value = response
    return provider


class TestGenerateInsightDefault:
    """Tests for generate_insight without persona (default behavior)."""

    def test_uses_default_prompt_when_no_persona(self) -> None:
        """persona 미설정 시 기본 INSIGHT_PROMPT를 사용한다."""
        article = _make_article()
        provider = _make_provider()

        generate_insight(article, provider, lang="en")

        prompt_arg = provider.generate.call_args[0][0]
        assert "intelligent reader" in prompt_arg
        assert "reader_profile" not in prompt_arg

    def test_returns_provider_response(self) -> None:
        """AI provider의 응답을 반환한다."""
        article = _make_article()
        provider = _make_provider("This matters because...")

        result = generate_insight(article, provider, lang="en")
        assert result == "This matters because..."

    def test_returns_none_when_unavailable(self) -> None:
        """provider가 사용 불가하면 None을 반환한다."""
        article = _make_article()
        provider = _make_provider()
        provider.is_available.return_value = False

        result = generate_insight(article, provider)
        assert result is None


class TestGenerateInsightPersona:
    """Tests for generate_insight with persona."""

    def test_uses_persona_prompt_when_set(self) -> None:
        """persona가 설정되면 INSIGHT_PROMPT_PERSONA를 사용한다."""
        article = _make_article()
        provider = _make_provider()

        generate_insight(article, provider, lang="en", persona="3년차 백엔드 개발자")

        prompt_arg = provider.generate.call_args[0][0]
        assert "reader_profile" in prompt_arg
        assert "3년차 백엔드 개발자" in prompt_arg
        assert "tailored to the reader's context" in prompt_arg

    def test_persona_includes_article_info(self) -> None:
        """persona 프롬프트에도 아티클 정보가 포함된다."""
        article = _make_article(title="Kubernetes 2.0", description="Major update")
        provider = _make_provider()

        generate_insight(article, provider, lang="ko", persona="DevOps engineer")

        prompt_arg = provider.generate.call_args[0][0]
        assert "Kubernetes 2.0" in prompt_arg
        assert "Major update" in prompt_arg
        assert "Korean" in prompt_arg

    def test_empty_persona_uses_default(self) -> None:
        """빈 문자열 persona는 기본 프롬프트를 사용한다."""
        article = _make_article()
        provider = _make_provider()

        generate_insight(article, provider, lang="en", persona="")

        prompt_arg = provider.generate.call_args[0][0]
        assert "intelligent reader" in prompt_arg
        assert "reader_profile" not in prompt_arg


class TestGetOrGenerateInsightPersona:
    """Tests for get_or_generate_insight with persona parameter."""

    def test_passes_persona_to_generate(self) -> None:
        """persona를 generate_insight에 전달한다."""
        article = _make_article()
        provider = _make_provider("Personalized insight")
        db = MagicMock()

        result = get_or_generate_insight(article, db, provider, persona="PM at startup")
        assert result == "Personalized insight"

        prompt_arg = provider.generate.call_args[0][0]
        assert "PM at startup" in prompt_arg

    def test_cached_insight_skips_generation(self) -> None:
        """캐시된 인사이트가 있으면 생성을 건너뛴다."""
        article = _make_article(insight="Cached insight")
        provider = _make_provider()
        db = MagicMock()

        result = get_or_generate_insight(article, db, provider, persona="any persona")
        assert result == "Cached insight"
        provider.generate.assert_not_called()


class TestInsightConfigPersona:
    """Tests for persona field in InsightConfig."""

    def test_default_persona_empty(self, tmp_path: Path) -> None:
        """persona 기본값은 빈 문자열이다."""
        config_file = tmp_path / "config.yml"
        config_file.write_text("feeds: []\n", encoding="utf-8")
        config = load_config(config_file)
        assert config.insight.persona == ""

    def test_persona_from_config(self, tmp_path: Path) -> None:
        """config에서 persona를 읽을 수 있다."""
        config_file = tmp_path / "config.yml"
        data = {
            "feeds": [],
            "insight": {
                "enabled": True,
                "mode": "manual",
                "persona": "3년차 프론트엔드 개발자, React/Next.js 전문",
            },
        }
        config_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
        config = load_config(config_file)
        assert config.insight.persona == "3년차 프론트엔드 개발자, React/Next.js 전문"
