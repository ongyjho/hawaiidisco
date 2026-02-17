"""Tests for OPML import/export."""
from __future__ import annotations

from pathlib import Path

import pytest

from hawaiidisco.config import FeedConfig
from hawaiidisco.opml import parse_opml, export_opml


# --- parse_opml ---


class TestParseOpml:
    """Tests for OPML file parsing."""

    def test_basic_opml(self, tmp_path: Path) -> None:
        """Parses feeds from a basic OPML file."""
        opml_file = tmp_path / "basic.opml"
        opml_file.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<opml version="2.0">\n'
            "  <head><title>Test</title></head>\n"
            "  <body>\n"
            '    <outline type="rss" text="Feed A" title="Feed A" xmlUrl="https://a.com/feed" />\n'
            '    <outline type="rss" text="Feed B" title="Feed B" xmlUrl="https://b.com/feed" />\n'
            "  </body>\n"
            "</opml>",
            encoding="utf-8",
        )
        feeds = parse_opml(opml_file)
        assert len(feeds) == 2
        assert feeds[0].name == "Feed A"
        assert feeds[0].url == "https://a.com/feed"
        assert feeds[1].name == "Feed B"

    def test_nested_opml(self, tmp_path: Path) -> None:
        """Recursively parses feeds from nested category outlines."""
        opml_file = tmp_path / "nested.opml"
        opml_file.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<opml version="2.0">\n'
            "  <head><title>Nested</title></head>\n"
            "  <body>\n"
            '    <outline text="Tech">\n'
            '      <outline type="rss" text="Feed A" xmlUrl="https://a.com/feed" />\n'
            '      <outline text="Sub Category">\n'
            '        <outline type="rss" text="Feed B" xmlUrl="https://b.com/feed" />\n'
            "      </outline>\n"
            "    </outline>\n"
            '    <outline type="rss" text="Feed C" xmlUrl="https://c.com/feed" />\n'
            "  </body>\n"
            "</opml>",
            encoding="utf-8",
        )
        feeds = parse_opml(opml_file)
        assert len(feeds) == 3
        urls = [f.url for f in feeds]
        assert "https://a.com/feed" in urls
        assert "https://b.com/feed" in urls
        assert "https://c.com/feed" in urls

    def test_empty_opml(self, tmp_path: Path) -> None:
        """OPML file with no feeds returns an empty list."""
        opml_file = tmp_path / "empty.opml"
        opml_file.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<opml version="2.0">\n'
            "  <head><title>Empty</title></head>\n"
            "  <body></body>\n"
            "</opml>",
            encoding="utf-8",
        )
        feeds = parse_opml(opml_file)
        assert feeds == []

    def test_invalid_xml_raises(self, tmp_path: Path) -> None:
        """Invalid XML raises an exception."""
        opml_file = tmp_path / "invalid.opml"
        opml_file.write_text("this is not xml", encoding="utf-8")
        with pytest.raises(Exception):
            parse_opml(opml_file)

    def test_no_body_returns_empty(self, tmp_path: Path) -> None:
        """Returns an empty list when body element is missing."""
        opml_file = tmp_path / "nobody.opml"
        opml_file.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<opml version="2.0">\n'
            "  <head><title>No Body</title></head>\n"
            "</opml>",
            encoding="utf-8",
        )
        feeds = parse_opml(opml_file)
        assert feeds == []

    def test_title_fallback_to_text(self, tmp_path: Path) -> None:
        """Falls back to text attribute when title attribute is missing."""
        opml_file = tmp_path / "text_only.opml"
        opml_file.write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<opml version="2.0">\n'
            "  <head><title>Test</title></head>\n"
            "  <body>\n"
            '    <outline type="rss" text="Text Name" xmlUrl="https://a.com/feed" />\n'
            "  </body>\n"
            "</opml>",
            encoding="utf-8",
        )
        feeds = parse_opml(opml_file)
        assert feeds[0].name == "Text Name"


# --- export_opml ---


class TestExportOpml:
    """Tests for OPML export."""

    def test_export_creates_file(self, tmp_path: Path) -> None:
        """Exports feeds to an OPML file."""
        feeds = [
            FeedConfig(url="https://a.com/feed", name="Feed A"),
            FeedConfig(url="https://b.com/feed", name="Feed B"),
        ]
        output = tmp_path / "output.opml"
        result = export_opml(feeds, output)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "Feed A" in content
        assert "https://a.com/feed" in content
        assert "Feed B" in content

    def test_export_empty_feeds(self, tmp_path: Path) -> None:
        """Empty feed list produces a valid OPML file."""
        output = tmp_path / "empty.opml"
        result = export_opml([], output)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "<body" in content

    def test_export_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Creates parent directories automatically."""
        output = tmp_path / "sub" / "dir" / "feeds.opml"
        feeds = [FeedConfig(url="https://a.com/feed", name="Feed A")]
        result = export_opml(feeds, output)
        assert result.exists()


# --- Roundtrip ---


class TestOpmlRoundtrip:
    """Import → export → import round-trip tests."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        """Re-importing exported OPML restores the same feeds."""
        original = [
            FeedConfig(url="https://a.com/feed", name="Feed A"),
            FeedConfig(url="https://b.com/feed", name="Feed B"),
            FeedConfig(url="https://c.com/rss", name="Feed C"),
        ]
        opml_path = tmp_path / "roundtrip.opml"
        export_opml(original, opml_path)

        imported = parse_opml(opml_path)
        assert len(imported) == len(original)
        for orig, imp in zip(original, imported):
            assert orig.url == imp.url
            assert orig.name == imp.name
