"""Tests for OPML import/export."""
from __future__ import annotations

from pathlib import Path

import pytest

from hawaiidisco.config import FeedConfig
from hawaiidisco.opml import parse_opml, export_opml


# --- parse_opml ---


class TestParseOpml:
    """OPML 파일 파싱 테스트."""

    def test_basic_opml(self, tmp_path: Path) -> None:
        """기본 OPML 파일에서 피드를 파싱한다."""
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
        """중첩된 카테고리 outline에서 피드를 재귀적으로 파싱한다."""
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
        """피드가 없는 OPML 파일은 빈 리스트를 반환한다."""
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
        """잘못된 XML은 예외를 발생시킨다."""
        opml_file = tmp_path / "invalid.opml"
        opml_file.write_text("this is not xml", encoding="utf-8")
        with pytest.raises(Exception):
            parse_opml(opml_file)

    def test_no_body_returns_empty(self, tmp_path: Path) -> None:
        """body 요소가 없으면 빈 리스트를 반환한다."""
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
        """title 속성이 없으면 text 속성을 이름으로 사용한다."""
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
    """OPML 내보내기 테스트."""

    def test_export_creates_file(self, tmp_path: Path) -> None:
        """피드를 OPML 파일로 내보낸다."""
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
        """빈 피드 목록도 유효한 OPML 파일을 생성한다."""
        output = tmp_path / "empty.opml"
        result = export_opml([], output)
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "<body" in content

    def test_export_creates_parent_dirs(self, tmp_path: Path) -> None:
        """부모 디렉토리가 없으면 자동 생성한다."""
        output = tmp_path / "sub" / "dir" / "feeds.opml"
        feeds = [FeedConfig(url="https://a.com/feed", name="Feed A")]
        result = export_opml(feeds, output)
        assert result.exists()


# --- Roundtrip ---


class TestOpmlRoundtrip:
    """import → export → import 라운드트립 테스트."""

    def test_roundtrip(self, tmp_path: Path) -> None:
        """내보낸 OPML을 다시 가져오면 동일한 피드가 복원된다."""
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
