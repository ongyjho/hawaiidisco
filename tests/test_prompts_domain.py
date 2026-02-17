"""Tests for domain-aware prompt templates."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from hawaiidisco.ai.base import AIProvider
from hawaiidisco.ai.prompts import (
    DIGEST_PROMPT,
    INSIGHT_PROMPT,
    INSIGHT_PROMPT_PERSONA,
)
from hawaiidisco.db import Article
from hawaiidisco.digest import generate_digest


def _make_article(**kwargs) -> Article:
    defaults = {
        "id": "abc123",
        "feed_name": "TestFeed",
        "title": "Test Article",
        "link": "https://example.com/article",
        "description": "Test description.",
        "published_at": datetime(2025, 1, 1),
        "fetched_at": datetime(2025, 1, 1),
        "is_read": False,
        "is_bookmarked": False,
        "insight": None,
    }
    defaults.update(kwargs)
    return Article(**defaults)


def _make_provider(response: str = "Generated content") -> MagicMock:
    provider = MagicMock(spec=AIProvider)
    provider.name = "mock"
    provider.is_available.return_value = True
    provider.generate.return_value = response
    return provider


class TestInsightPromptDomainAware:
    """Verify INSIGHT_PROMPT includes domain-aware instructions."""

    def test_domain_identification_instruction(self) -> None:
        """Prompt instructs AI to identify article domain."""
        assert "identify the article's domain" in INSIGHT_PROMPT

    def test_lists_multiple_domains(self) -> None:
        """Prompt lists various domains including non-tech ones."""
        for domain in ("politics", "business", "economics", "science", "culture", "sports"):
            assert domain in INSIGHT_PROMPT, f"Missing domain: {domain}"

    def test_no_tech_bias(self) -> None:
        """Prompt explicitly forbids tech-biased analysis on non-tech articles."""
        assert "Do NOT analyze non-tech articles from a technical perspective" in INSIGHT_PROMPT

    def test_domain_specific_examples(self) -> None:
        """Prompt provides domain-specific analysis examples."""
        assert "political/policy perspective" in INSIGHT_PROMPT
        assert "market/strategy perspective" in INSIGHT_PROMPT


class TestInsightPromptPersonaDomainAware:
    """Verify INSIGHT_PROMPT_PERSONA handles cross-domain articles."""

    def test_domain_identification_instruction(self) -> None:
        """Persona prompt also instructs domain identification."""
        assert "identify the article's domain" in INSIGHT_PROMPT_PERSONA

    def test_no_forced_tech_analysis(self) -> None:
        """Persona prompt forbids forcing tech analysis."""
        assert "Do NOT force a technical analysis on non-tech articles" in INSIGHT_PROMPT_PERSONA

    def test_cross_domain_instruction(self) -> None:
        """Instructs to analyze from article's own domain when outside reader's domain."""
        assert "outside the reader's primary domain" in INSIGHT_PROMPT_PERSONA
        assert "article's own domain perspective first" in INSIGHT_PROMPT_PERSONA

    def test_within_domain_tailoring(self) -> None:
        """Tailors insight when article is within reader's domain."""
        assert "within the reader's primary domain" in INSIGHT_PROMPT_PERSONA
        assert "tailored to their role" in INSIGHT_PROMPT_PERSONA

    def test_format_with_political_article(self) -> None:
        """Persona prompt can be formatted with a political article."""
        prompt = INSIGHT_PROMPT_PERSONA.format(
            persona="Senior backend engineer",
            output_language="Korean",
            title="대통령 탄핵안 가결",
            description="국회에서 대통령 탄핵소추안이 가결되었다.",
        )
        assert "대통령 탄핵안 가결" in prompt
        assert "Senior backend engineer" in prompt
        assert "outside the reader's primary domain" in prompt


class TestDigestPromptDomainAware:
    """Verify DIGEST_PROMPT is domain-neutral."""

    def test_no_tech_editor_hardcoding(self) -> None:
        """Digest prompt does not hardcode 'tech editor'."""
        assert "tech editor" not in DIGEST_PROMPT

    def test_senior_editor_role(self) -> None:
        """Digest prompt uses generic 'senior editor' role."""
        assert "senior editor" in DIGEST_PROMPT

    def test_no_engineer_implications(self) -> None:
        """Digest prompt does not hardcode 'implications for engineers'."""
        assert "implications for engineers" not in DIGEST_PROMPT

    def test_domain_perspective_instruction(self) -> None:
        """Digest prompt instructs domain-aware analysis."""
        assert "from its own domain perspective" in DIGEST_PROMPT

    def test_lists_domain_examples(self) -> None:
        """Digest prompt mentions various domains."""
        assert "tech, politics, business" in DIGEST_PROMPT


class TestDigestGenerationPrompt:
    """Test that generate_digest passes the domain-aware prompt to the provider."""

    def test_digest_prompt_sent_to_provider(self) -> None:
        """generate_digest sends the domain-aware prompt to AI provider."""
        articles = [
            _make_article(
                id="pol1",
                title="Election Results",
                description="New government formed.",
                feed_name="PoliticsFeed",
            ),
            _make_article(
                id="tech1",
                title="New JS Framework",
                description="A new frontend framework.",
                feed_name="TechFeed",
            ),
        ]
        provider = _make_provider("Weekly digest content")

        result = generate_digest(articles, provider, period_days=7, lang="en")

        assert result == "Weekly digest content"
        prompt_arg = provider.generate.call_args[0][0]
        assert "senior editor" in prompt_arg
        assert "tech editor" not in prompt_arg
        assert "from its own domain perspective" in prompt_arg
        assert "Election Results" in prompt_arg
        assert "New JS Framework" in prompt_arg

    def test_digest_prompt_contains_all_articles(self) -> None:
        """All articles appear in the formatted prompt."""
        articles = [
            _make_article(id=f"a{i}", title=f"Article {i}", feed_name=f"Feed{i}")
            for i in range(5)
        ]
        provider = _make_provider()

        generate_digest(articles, provider, period_days=3, lang="ko")

        prompt_arg = provider.generate.call_args[0][0]
        for i in range(5):
            assert f"Article {i}" in prompt_arg
        assert "Korean" in prompt_arg
