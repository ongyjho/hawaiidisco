"""OPML import/export support."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from hawaiidisco.config import FeedConfig

# Maximum OPML file size (1 MB) to prevent XML bomb attacks
_MAX_OPML_SIZE = 1_048_576


def parse_opml(source: str | Path) -> list[FeedConfig]:
    """OPML 파일을 파싱하여 FeedConfig 리스트를 반환한다.

    중첩된 outline 요소를 재귀적으로 탐색한다.
    """
    path = Path(source)

    # Guard against XML bomb / excessively large files
    if path.stat().st_size > _MAX_OPML_SIZE:
        msg = f"OPML file too large (>{_MAX_OPML_SIZE} bytes)"
        raise ValueError(msg)

    try:
        import defusedxml.ElementTree as SafeET

        tree = SafeET.parse(path)
    except ImportError:
        tree = ET.parse(path)  # noqa: S314
    root = tree.getroot()

    body = root.find("body")
    if body is None:
        return []

    feeds: list[FeedConfig] = []
    _collect_feeds(body, feeds)
    return feeds


def _collect_feeds(element: ET.Element, feeds: list[FeedConfig]) -> None:
    """outline 요소를 재귀 탐색하여 xmlUrl이 있는 항목을 수집한다."""
    for outline in element.findall("outline"):
        xml_url = outline.get("xmlUrl")
        if xml_url and xml_url.startswith(("http://", "https://")):
            name = outline.get("title") or outline.get("text") or xml_url
            feeds.append(FeedConfig(url=xml_url, name=name))
        # 하위 outline 재귀 탐색 (카테고리 폴더)
        _collect_feeds(outline, feeds)


def export_opml(
    feeds: list[FeedConfig],
    output_path: str | Path,
    title: str = "Hawaii Disco Feeds",
) -> Path:
    """피드 목록을 OPML 2.0 파일로 내보낸다."""
    opml = ET.Element("opml", version="2.0")

    head = ET.SubElement(opml, "head")
    title_el = ET.SubElement(head, "title")
    title_el.text = title
    date_el = ET.SubElement(head, "dateCreated")
    date_el.text = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    body = ET.SubElement(opml, "body")
    for feed in feeds:
        ET.SubElement(
            body,
            "outline",
            type="rss",
            text=feed.name,
            title=feed.name,
            xmlUrl=feed.url,
        )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(opml)
    ET.indent(tree, space="  ")
    tree.write(str(path), encoding="unicode", xml_declaration=True)
    return path
