from __future__ import annotations

import shutil
import sqlite3
from contextlib import contextmanager
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MEDIA_DIR = DATA_DIR / "media"
PDF_DIR = MEDIA_DIR / "pdfs"
LEGACY_IMAGE_DIR = MEDIA_DIR / "articles"
DB_PATH = DATA_DIR / "shitspace.db"

EXPECTED_ARTICLE_COLUMNS = {
    "id",
    "title",
    "author_name",
    "tag",
    "discipline",
    "zone",
    "created_at",
    "approved_at",
    "source_updated_at",
    "rating_count",
    "avg_score",
    "comment_count",
    "page_count",
    "generated_pdf_path",
    "crawled_at",
}

EXPECTED_COMMENT_COLUMNS = {
    "id",
    "article_id",
    "parent_id",
    "content",
    "element_type",
    "like_count",
    "created_at",
    "user_id",
    "user_display_name",
    "user_avatar_url",
    "my_vote",
    "crawled_at",
}

EXPECTED_CONTENT_COLUMNS = {
    "id",
    "content_type",
    "title",
    "content",
    "author_name",
    "author_avatar",
    "tag",
    "status",
    "created_at",
    "updated_at",
    "rating_count",
    "avg_score",
    "comment_count",
    "view_count",
    "like_count",
    "source_url",
    "crawled_at",
}

EXPECTED_CONTENT_COMMENTS_COLUMNS = {
    "id",
    "content_id",
    "content_type",
    "parent_id",
    "content",
    "like_count",
    "created_at",
    "user_id",
    "user_display_name",
    "user_avatar_url",
    "crawled_at",
}


def row_factory(cursor: sqlite3.Cursor, row: tuple[object, ...]) -> dict[str, object]:
    return {column[0]: row[index] for index, column in enumerate(cursor.description)}


@contextmanager
def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    MEDIA_DIR.mkdir(parents=True, exist_ok=True)
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = row_factory
    connection.execute("PRAGMA foreign_keys = ON;")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def init_db() -> None:
    with get_connection() as connection:
        article_columns = table_columns(connection, "articles")
        comment_columns = table_columns(connection, "article_comments")
        content_columns = table_columns(connection, "contents")
        content_comment_columns = table_columns(connection, "content_comments")

        if article_columns and article_columns != EXPECTED_ARTICLE_COLUMNS:
            connection.executescript(
                """
                DROP TABLE IF EXISTS article_comments;
                DROP TABLE IF EXISTS article_pages;
                DROP TABLE IF EXISTS articles;
                """
            )
            article_columns = set()

        if comment_columns and comment_columns != EXPECTED_COMMENT_COLUMNS:
            connection.execute("DROP TABLE IF EXISTS article_comments")

        if content_columns and content_columns != EXPECTED_CONTENT_COLUMNS:
            connection.execute("DROP TABLE IF EXISTS content_comments")
            connection.execute("DROP TABLE IF EXISTS contents")
            content_columns = set()

        if content_comment_columns and content_comment_columns != EXPECTED_CONTENT_COMMENTS_COLUMNS:
            connection.execute("DROP TABLE IF EXISTS content_comments")

        connection.executescript(
            """
            DROP TABLE IF EXISTS article_pages;

            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                author_name TEXT,
                tag TEXT,
                discipline TEXT,
                zone TEXT,
                created_at TEXT,
                approved_at TEXT,
                source_updated_at TEXT,
                rating_count INTEGER DEFAULT 0,
                avg_score REAL DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                page_count INTEGER DEFAULT 0,
                generated_pdf_path TEXT,
                crawled_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS article_comments (
                id TEXT PRIMARY KEY,
                article_id TEXT NOT NULL,
                parent_id TEXT,
                content TEXT NOT NULL,
                element_type TEXT,
                like_count INTEGER DEFAULT 0,
                created_at TEXT,
                user_id TEXT,
                user_display_name TEXT,
                user_avatar_url TEXT,
                my_vote INTEGER DEFAULT 0,
                crawled_at TEXT NOT NULL,
                FOREIGN KEY(article_id) REFERENCES articles(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS contents (
                id TEXT PRIMARY KEY,
                content_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT,
                author_name TEXT,
                author_avatar TEXT,
                tag TEXT,
                status TEXT,
                created_at TEXT,
                updated_at TEXT,
                rating_count INTEGER DEFAULT 0,
                avg_score REAL DEFAULT 0,
                comment_count INTEGER DEFAULT 0,
                view_count INTEGER DEFAULT 0,
                like_count INTEGER DEFAULT 0,
                source_url TEXT,
                crawled_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS content_comments (
                id TEXT PRIMARY KEY,
                content_id TEXT NOT NULL,
                content_type TEXT NOT NULL,
                parent_id TEXT,
                content TEXT NOT NULL,
                like_count INTEGER DEFAULT 0,
                created_at TEXT,
                user_id TEXT,
                user_display_name TEXT,
                user_avatar_url TEXT,
                crawled_at TEXT NOT NULL,
                FOREIGN KEY(content_id) REFERENCES contents(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_articles_created_at
            ON articles(created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_articles_updated_at
            ON articles(source_updated_at DESC);

            CREATE INDEX IF NOT EXISTS idx_articles_zone
            ON articles(zone);

            CREATE INDEX IF NOT EXISTS idx_articles_tag
            ON articles(tag);

            CREATE INDEX IF NOT EXISTS idx_comments_article_created_at
            ON article_comments(article_id, created_at ASC);

            CREATE INDEX IF NOT EXISTS idx_contents_type
            ON contents(content_type);

            CREATE INDEX IF NOT EXISTS idx_contents_created_at
            ON contents(created_at DESC);

            CREATE INDEX IF NOT EXISTS idx_content_comments_content
            ON content_comments(content_id, content_type, created_at ASC);

            CREATE TABLE IF NOT EXISTS homepage_data (
                key TEXT PRIMARY KEY,
                data_type TEXT NOT NULL,
                content TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    if LEGACY_IMAGE_DIR.exists():
        shutil.rmtree(LEGACY_IMAGE_DIR, ignore_errors=True)
