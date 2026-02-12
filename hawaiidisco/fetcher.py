"""RSS feed fetching and parsing."""
from __future__ import annotations

import hashlib
import logging
import re
import ssl
import urllib.request
from datetime import datetime
from time import mktime

import feedparser

from hawaiidisco.config import FeedConfig
from hawaiidisco.db import Database
from hawaiidisco.i18n import t

logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _make_ssl_handler() -> urllib.request.HTTPSHandler:
    """Create an HTTPS handler that bypasses SSL certificate verification."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.HTTPSHandler(context=ctx)


def _make_article_id(entry: dict, feed_name: str) -> str:
    """Generate a unique ID by hashing the guid or link."""
    guid = entry.get("id") or entry.get("link", "")
    return hashlib.sha256(f"{feed_name}:{guid}".encode()).hexdigest()[:16]


def _parse_published(entry: dict) -> datetime | None:
    """Parse the published or updated timestamp from an entry."""
    for key in ("published_parsed", "updated_parsed"):
        parsed = entry.get(key)
        if parsed:
            try:
                return datetime.fromtimestamp(mktime(parsed))
            except (ValueError, OverflowError):
                continue
    return None


def fetch_feed(feed_config: FeedConfig, db: Database) -> int:
    """Fetch a single feed and store it in the database. Return the number of new articles."""
    # Try default first; fall back to SSL bypass on failure
    parsed = feedparser.parse(feed_config.url, agent=USER_AGENT)
    if parsed.bozo and not parsed.entries:
        parsed = feedparser.parse(
            feed_config.url,
            agent=USER_AGENT,
            handlers=[_make_ssl_handler()],
        )

    new_count = 0
    for entry in parsed.entries:
        article_id = _make_article_id(entry, feed_config.name)
        title = entry.get("title", t("no_title"))
        link = entry.get("link", "")
        description = entry.get("summary", entry.get("description", ""))
        # Strip HTML tags
        if description:
            description = re.sub(r"<[^>]+>", "", description).strip()
            if len(description) > 500:
                description = description[:500] + "..."
        published_at = _parse_published(entry)

        is_new = db.upsert_article(
            article_id=article_id,
            feed_name=feed_config.name,
            title=title,
            link=link,
            description=description,
            published_at=published_at,
        )
        if is_new:
            new_count += 1

    return new_count


def fetch_all_feeds(feeds: list[FeedConfig], db: Database) -> int:
    """Fetch all feeds. Return the total number of new articles."""
    total_new = 0
    for feed_config in feeds:
        try:
            total_new += fetch_feed(feed_config, db)
        except Exception:
            logger.debug("피드 가져오기 실패: %s", feed_config.url, exc_info=True)
            continue
    return total_new
