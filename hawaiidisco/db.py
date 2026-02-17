"""SQLite database management."""
from __future__ import annotations

import os
import sqlite3
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Article:
    id: str
    feed_name: str
    title: str
    link: str
    description: str | None
    published_at: datetime | None
    fetched_at: datetime
    is_read: bool
    is_bookmarked: bool
    insight: str | None
    translated_title: str | None = None
    translated_desc: str | None = None
    translated_body: str | None = None


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    feed_name TEXT NOT NULL,
    title TEXT NOT NULL,
    link TEXT NOT NULL,
    description TEXT,
    published_at DATETIME,
    fetched_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_read INTEGER DEFAULT 0,
    is_bookmarked INTEGER DEFAULT 0,
    insight TEXT
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id TEXT NOT NULL REFERENCES articles(id),
    bookmarked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    tags TEXT,
    memo TEXT
);

"""


class Database:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._local = threading.local()
        # Initialize schema on the main thread
        conn = self._get_conn()
        conn.executescript(SCHEMA_SQL)
        self._migrate(conn)
        conn.commit()
        # Restrict database file to owner-only access
        if str(db_path) != ":memory:":
            try:
                os.chmod(db_path, 0o600)
            except OSError:
                pass

    def _get_conn(self) -> sqlite3.Connection:
        """Return a thread-local database connection."""
        conn = getattr(self._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA journal_mode=WAL")
            conn.row_factory = sqlite3.Row
            self._local.conn = conn
        return conn

    def _migrate(self, conn: sqlite3.Connection) -> None:
        """Add new columns and indexes to existing tables if missing."""
        cursor = conn.execute("PRAGMA table_info(articles)")
        columns = {row[1] for row in cursor.fetchall()}
        if "translated_title" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN translated_title TEXT")
        if "translated_desc" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN translated_desc TEXT")
        if "translated_body" not in columns:
            conn.execute("ALTER TABLE articles ADD COLUMN translated_body TEXT")
        # Performance indexes for common query patterns
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_published "
            "ON articles(published_at DESC, fetched_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_feed "
            "ON articles(feed_name, published_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_articles_read "
            "ON articles(is_read, published_at DESC)"
        )

    def close(self) -> None:
        conn = getattr(self._local, "conn", None)
        if conn:
            conn.close()
            self._local.conn = None

    # --- Article Operations ---

    def upsert_article(
        self,
        article_id: str,
        feed_name: str,
        title: str,
        link: str,
        description: str | None,
        published_at: datetime | None,
    ) -> bool:
        """Insert an article or ignore if it already exists. Return True if newly inserted."""
        cursor = self._get_conn().execute(
            "INSERT OR IGNORE INTO articles (id, feed_name, title, link, description, published_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (article_id, feed_name, title, link, description, published_at),
        )
        self._get_conn().commit()
        return cursor.rowcount > 0

    def get_articles(
        self,
        *,
        bookmarked_only: bool = False,
        search: str | None = None,
        feed_name: str | None = None,
        unread_only: bool = False,
        limit: int = 200,
    ) -> list[Article]:
        """Return a list of articles ordered by most recent first."""
        query = "SELECT * FROM articles WHERE 1=1"
        params: list = []
        if bookmarked_only:
            query += " AND is_bookmarked = 1"
        if unread_only:
            query += " AND is_read = 0"
        if feed_name:
            query += " AND feed_name = ?"
            params.append(feed_name)
        if search:
            # LIKE 와일드카드 문자 이스케이프
            escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped}%"
            query += (
                " AND (title LIKE ? ESCAPE '\\'"
                " OR description LIKE ? ESCAPE '\\'"
                " OR insight LIKE ? ESCAPE '\\'"
                " OR translated_title LIKE ? ESCAPE '\\'"
                " OR translated_desc LIKE ? ESCAPE '\\')"
            )
            params.extend([pattern] * 5)
        query += " ORDER BY published_at DESC, fetched_at DESC LIMIT ?"
        params.append(limit)

        rows = self._get_conn().execute(query, params).fetchall()
        return [self._row_to_article(row) for row in rows]

    def get_article(self, article_id: str) -> Article | None:
        row = self._get_conn().execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return self._row_to_article(row) if row else None

    def mark_read(self, article_id: str) -> None:
        self._get_conn().execute(
            "UPDATE articles SET is_read = 1 WHERE id = ?", (article_id,)
        )
        self._get_conn().commit()

    def toggle_bookmark(self, article_id: str) -> bool:
        """Toggle the bookmark state of an article. Return the new state."""
        article = self.get_article(article_id)
        if not article:
            return False
        new_state = not article.is_bookmarked
        self._get_conn().execute(
            "UPDATE articles SET is_bookmarked = ? WHERE id = ?",
            (int(new_state), article_id),
        )
        if new_state:
            self._get_conn().execute(
                "INSERT INTO bookmarks (article_id) VALUES (?)", (article_id,)
            )
        else:
            self._get_conn().execute(
                "DELETE FROM bookmarks WHERE article_id = ?", (article_id,)
            )
        self._get_conn().commit()
        return new_state

    def set_insight(self, article_id: str, insight: str) -> None:
        self._get_conn().execute(
            "UPDATE articles SET insight = ? WHERE id = ?", (insight, article_id)
        )
        self._get_conn().commit()

    def set_translation(self, article_id: str, title: str, desc: str) -> None:
        self._get_conn().execute(
            "UPDATE articles SET translated_title = ?, translated_desc = ? WHERE id = ?",
            (title, desc, article_id),
        )
        self._get_conn().commit()

    def set_translated_body(self, article_id: str, translated_body: str) -> None:
        self._get_conn().execute(
            "UPDATE articles SET translated_body = ? WHERE id = ?",
            (translated_body, article_id),
        )
        self._get_conn().commit()

    def get_translated_body(self, article_id: str) -> str | None:
        row = self._get_conn().execute(
            "SELECT translated_body FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return row["translated_body"] if row else None

    def set_bookmark_memo(self, article_id: str, memo: str) -> None:
        self._get_conn().execute(
            "UPDATE bookmarks SET memo = ? WHERE article_id = ?",
            (memo, article_id),
        )
        self._get_conn().commit()

    def get_bookmark_memo(self, article_id: str) -> str | None:
        row = self._get_conn().execute(
            "SELECT memo FROM bookmarks WHERE article_id = ?", (article_id,)
        ).fetchone()
        return row["memo"] if row else None

    def delete_articles_by_feed(self, feed_name: str) -> int:
        """Delete all articles (and their bookmarks) belonging to a feed. Return deleted count."""
        conn = self._get_conn()
        # 먼저 bookmarks FK 참조 삭제
        conn.execute(
            "DELETE FROM bookmarks WHERE article_id IN "
            "(SELECT id FROM articles WHERE feed_name = ?)",
            (feed_name,),
        )
        cursor = conn.execute(
            "DELETE FROM articles WHERE feed_name = ?", (feed_name,)
        )
        conn.commit()
        return cursor.rowcount

    # --- Tag Operations ---

    def set_bookmark_tags(self, article_id: str, tags: list[str]) -> None:
        """북마크의 태그를 저장한다. 빈 리스트면 NULL로 설정."""
        value = ",".join(t.strip() for t in tags if t.strip()) or None
        self._get_conn().execute(
            "UPDATE bookmarks SET tags = ? WHERE article_id = ?",
            (value, article_id),
        )
        self._get_conn().commit()

    def get_bookmark_tags(self, article_id: str) -> list[str]:
        """북마크의 태그 리스트를 반환한다."""
        row = self._get_conn().execute(
            "SELECT tags FROM bookmarks WHERE article_id = ?", (article_id,)
        ).fetchone()
        if not row or not row["tags"]:
            return []
        return [t.strip() for t in row["tags"].split(",") if t.strip()]

    def get_all_tags(self) -> list[str]:
        """모든 태그를 중복 없이 반환한다."""
        rows = self._get_conn().execute(
            "SELECT tags FROM bookmarks WHERE tags IS NOT NULL AND tags != ''"
        ).fetchall()
        tag_set: set[str] = set()
        for row in rows:
            for tag in row["tags"].split(","):
                stripped = tag.strip()
                if stripped:
                    tag_set.add(stripped)
        return sorted(tag_set)

    def get_articles_by_tag(self, tag: str) -> list[Article]:
        """특정 태그가 붙은 북마크 글을 반환한다."""
        # 쉼표 구분 문자열에서 정확한 태그 매칭: 시작/중간/끝 패턴
        rows = self._get_conn().execute(
            "SELECT a.* FROM articles a JOIN bookmarks b ON a.id = b.article_id "
            "WHERE b.tags = ? "
            "OR b.tags LIKE ? "
            "OR b.tags LIKE ? "
            "OR b.tags LIKE ? "
            "ORDER BY a.published_at DESC, a.fetched_at DESC",
            (tag, f"{tag},%", f"%,{tag},%", f"%,{tag}"),
        ).fetchall()
        return [self._row_to_article(row) for row in rows]

    def get_all_bookmark_tags(self) -> dict[str, list[str]]:
        """모든 북마크의 태그를 ``{article_id: [tags]}`` 형태로 반환한다."""
        rows = self._get_conn().execute(
            "SELECT article_id, tags FROM bookmarks "
            "WHERE tags IS NOT NULL AND tags != ''"
        ).fetchall()
        result: dict[str, list[str]] = {}
        for row in rows:
            tags = [t.strip() for t in row["tags"].split(",") if t.strip()]
            if tags:
                result[row["article_id"]] = tags
        return result

    # --- Feed / Bookmark Statistics ---

    def get_article_count_by_feed(self) -> dict[str, int]:
        """Return article counts grouped by feed name."""
        rows = self._get_conn().execute(
            "SELECT feed_name, COUNT(*) as cnt FROM articles GROUP BY feed_name"
        ).fetchall()
        return {row["feed_name"]: row["cnt"] for row in rows}

    def get_all_bookmark_memos(self) -> dict[str, str]:
        """Return all bookmark memos as ``{article_id: memo}``."""
        rows = self._get_conn().execute(
            "SELECT article_id, memo FROM bookmarks "
            "WHERE memo IS NOT NULL AND memo != ''"
        ).fetchall()
        return {row["article_id"]: row["memo"] for row in rows}

    def get_recent_bookmarked_articles(self, days: int = 7) -> list[Article]:
        """최근 N일간 북마크한 글을 반환한다."""
        rows = self._get_conn().execute(
            "SELECT a.* FROM articles a JOIN bookmarks b ON a.id = b.article_id "
            "WHERE b.bookmarked_at >= datetime('now', ?) ORDER BY b.bookmarked_at DESC, b.id DESC",
            (f"-{days} days",),
        ).fetchall()
        return [self._row_to_article(row) for row in rows]

    # --- Internal Utilities ---

    @staticmethod
    def _row_to_article(row: sqlite3.Row) -> Article:
        keys = row.keys()
        return Article(
            id=row["id"],
            feed_name=row["feed_name"],
            title=row["title"],
            link=row["link"],
            description=row["description"],
            published_at=_parse_dt(row["published_at"]),
            fetched_at=_parse_dt(row["fetched_at"]) or datetime.now(),
            is_read=bool(row["is_read"]),
            is_bookmarked=bool(row["is_bookmarked"]),
            insight=row["insight"],
            translated_title=row["translated_title"] if "translated_title" in keys else None,
            translated_desc=row["translated_desc"] if "translated_desc" in keys else None,
            translated_body=row["translated_body"] if "translated_body" in keys else None,
        )


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
