"""Fetch and extract article body text from web pages."""
from __future__ import annotations

import logging
import re
import ssl
import urllib.error
import urllib.request
from html.parser import HTMLParser

from hawaiidisco.i18n import t

logger = logging.getLogger(__name__)


_SKIP_TAGS = {"script", "style", "noscript", "header", "footer", "nav", "aside", "iframe"}


class _TextExtractor(HTMLParser):
    """Extract body text from HTML."""

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0
        self._in_block = False

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        if tag in ("p", "div", "article", "section", "li", "h1", "h2", "h3", "h4", "h5", "h6", "br", "tr"):
            self._chunks.append("\n")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._chunks.append("## " if tag != "h1" else "# ")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag in ("p", "div", "article", "section", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self._chunks.append(text)

    def get_text(self) -> str:
        raw = " ".join(self._chunks)
        # Normalize consecutive whitespace and newlines
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n ", "\n", raw)
        raw = re.sub(r" \n", "\n", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()


def _make_insecure_context() -> ssl.SSLContext:
    """SSL 검증을 비활성화한 컨텍스트 (폴백 전용)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


_BROWSER_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_HEADERS = {
    "User-Agent": _BROWSER_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _urlopen(url: str, timeout: int, ctx: ssl.SSLContext | None = None) -> str:
    """URL을 열어 HTML을 반환한다."""
    req = urllib.request.Request(url, headers=_HEADERS)
    kwargs: dict = {"timeout": timeout}
    if ctx is not None:
        kwargs["context"] = ctx
    with urllib.request.urlopen(req, **kwargs) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def fetch_article_text(url: str, timeout: int = 15, *, allow_insecure_ssl: bool = False) -> str:
    """Extract body text from the given URL."""
    try:
        html = _urlopen(url, timeout)
    except Exception as first_err:
        if not allow_insecure_ssl:
            logger.debug("Fetch failed (%s): %s", first_err, url)
            return t("fetch_error", error=type(first_err).__name__)
        logger.warning("SSL verification failed for %s, retrying without verification", url)
        try:
            html = _urlopen(url, timeout, ctx=_make_insecure_context())
        except Exception as e:
            logger.debug("Insecure fallback also failed: %s", e)
            return t("fetch_error", error=type(e).__name__)

    extractor = _TextExtractor()
    extractor.feed(html)
    text = extractor.get_text()

    if not text:
        return t("extract_error")

    # Truncate if too long
    if len(text) > 10000:
        text = text[:10000] + "\n\n" + t("truncated")

    return text
