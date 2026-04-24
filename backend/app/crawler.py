from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import fitz
import requests
from PIL import Image
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .db import MEDIA_DIR, PDF_DIR, get_connection


SOURCE_BASE_URL = "https://shitspace.xyz"
LIST_ENDPOINT = f"{SOURCE_BASE_URL}/api/articles/"
DETAIL_ENDPOINT = f"{SOURCE_BASE_URL}/api/articles/{{article_id}}"
COMMENTS_ENDPOINT = f"{SOURCE_BASE_URL}/api/articles/{{article_id}}/comments"
DEFAULT_TIMEOUT = 30
DEFAULT_RENDER_SCALE = 3.0
DEFAULT_CRAWL_WINDOW_DAYS = 5
COMMENTS_PAGE_SIZE = 100
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


@dataclass
class CrawlResult:
    requested_pages: int
    fetched_pages: int
    fetched_articles: int
    saved_articles: int
    regenerated_articles: int
    rendered_pages: int
    generated_pdfs: int
    saved_comments: int
    pruned_articles: int
    deleted_pdfs: int
    source_total_count: int
    source_total_pages: int
    crawl_window_days: int
    cutoff_at: str
    crawled_at: str


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Referer": f"{SOURCE_BASE_URL}/articles",
        }
    )
    retry = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=0.8,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def _parse_json(response: requests.Response) -> Any:
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.json()


def fetch_article_page(session: requests.Session, page: int) -> dict[str, Any]:
    response = session.get(LIST_ENDPOINT, params={"page": page}, timeout=DEFAULT_TIMEOUT)
    return _parse_json(response)


def fetch_article_detail(session: requests.Session, article_id: str) -> dict[str, Any]:
    response = session.get(
        DETAIL_ENDPOINT.format(article_id=article_id),
        timeout=DEFAULT_TIMEOUT,
    )
    return _parse_json(response)


def fetch_article_comments(session: requests.Session, article_id: str) -> list[dict[str, Any]]:
    comments: list[dict[str, Any]] = []
    page = 1
    total_pages = 1

    while page <= total_pages:
        response = session.get(
            COMMENTS_ENDPOINT.format(article_id=article_id),
            params={"page": page, "page_size": COMMENTS_PAGE_SIZE},
            timeout=DEFAULT_TIMEOUT,
        )
        payload = _parse_json(response)
        comments.extend(payload.get("data", []))
        total_pages = max(int(payload.get("total_pages") or 0), 1)
        page += 1

    return comments


def download_pdf_bytes(session: requests.Session, pdf_url: str | None) -> bytes | None:
    if not pdf_url:
        return None
    response = session.get(pdf_url, timeout=DEFAULT_TIMEOUT)
    response.raise_for_status()
    return response.content


def parse_source_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def isoformat_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def article_reference_time(article: dict[str, Any]) -> datetime | None:
    for key in ("approved_at", "created_at", "updated_at", "source_updated_at"):
        parsed = parse_source_datetime(article.get(key))
        if parsed:
            return parsed
    return None


def is_recent_article(article: dict[str, Any], cutoff_at: datetime) -> bool:
    reference_time = article_reference_time(article)
    if reference_time is None:
        return True
    return reference_time >= cutoff_at


def load_existing_articles() -> dict[str, dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, source_updated_at, generated_pdf_path, page_count
            FROM articles
            """
        ).fetchall()
    return {row["id"]: row for row in rows}


def article_needs_regeneration(
    existing: dict[str, Any] | None,
    list_item: dict[str, Any],
) -> bool:
    if not existing:
        return True

    pdf_path = existing.get("generated_pdf_path")
    full_pdf_path = MEDIA_DIR / str(pdf_path) if pdf_path else None
    if not pdf_path or not full_pdf_path or not full_pdf_path.exists():
        return True

    if int(existing.get("page_count") or 0) <= 0:
        return True

    return existing.get("source_updated_at") != list_item.get("updated_at")


def render_pdf_to_images(
    pdf_bytes: bytes,
    render_scale: float,
) -> list[Image.Image]:
    document = fitz.open(stream=pdf_bytes, filetype="pdf")
    images: list[Image.Image] = []
    try:
        matrix = fitz.Matrix(render_scale, render_scale)
        for page_index in range(document.page_count):
            page = document.load_page(page_index)
            pixmap = page.get_pixmap(matrix=matrix, alpha=False)
            image = Image.open(BytesIO(pixmap.tobytes("png")))
            images.append(image.convert("RGB"))
    finally:
        document.close()
    return images


def build_pdf_from_images(article_id: str, images: list[Image.Image]) -> str | None:
    if not images:
        return None

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PDF_DIR / f"{article_id}.pdf"
    first, rest = images[0], images[1:]
    first.save(output_path, save_all=True, append_images=rest)
    return str(output_path.relative_to(MEDIA_DIR)).replace("\\", "/")


def close_images(images: list[Image.Image]) -> None:
    for image in images:
        image.close()


def upsert_article(
    article_id: str,
    title: str,
    author_name: str | None,
    tag: str | None,
    discipline: str | None,
    zone: str | None,
    created_at: str | None,
    approved_at: str | None,
    source_updated_at: str | None,
    rating_count: int,
    avg_score: float,
    comment_count: int,
    page_count: int,
    generated_pdf_path: str | None,
    crawled_at: str,
) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO articles (
                id, title, author_name, tag, discipline, zone, created_at,
                approved_at, source_updated_at, rating_count, avg_score,
                comment_count, page_count, generated_pdf_path, crawled_at
            ) VALUES (
                :id, :title, :author_name, :tag, :discipline, :zone, :created_at,
                :approved_at, :source_updated_at, :rating_count, :avg_score,
                :comment_count, :page_count, :generated_pdf_path, :crawled_at
            )
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                author_name = excluded.author_name,
                tag = excluded.tag,
                discipline = excluded.discipline,
                zone = excluded.zone,
                created_at = excluded.created_at,
                approved_at = excluded.approved_at,
                source_updated_at = excluded.source_updated_at,
                rating_count = excluded.rating_count,
                avg_score = excluded.avg_score,
                comment_count = excluded.comment_count,
                page_count = excluded.page_count,
                generated_pdf_path = COALESCE(excluded.generated_pdf_path, articles.generated_pdf_path),
                crawled_at = excluded.crawled_at
            """,
            {
                "id": article_id,
                "title": title,
                "author_name": author_name,
                "tag": tag,
                "discipline": discipline,
                "zone": zone,
                "created_at": created_at,
                "approved_at": approved_at,
                "source_updated_at": source_updated_at,
                "rating_count": rating_count,
                "avg_score": avg_score,
                "comment_count": comment_count,
                "page_count": page_count,
                "generated_pdf_path": generated_pdf_path,
                "crawled_at": crawled_at,
            },
        )


def replace_article_comments(
    article_id: str,
    comments: list[dict[str, Any]],
    crawled_at: str,
) -> int:
    with get_connection() as connection:
        connection.execute("DELETE FROM article_comments WHERE article_id = ?", [article_id])
        for comment in comments:
            user = comment.get("user") or {}
            connection.execute(
                """
                INSERT INTO article_comments (
                    id, article_id, parent_id, content, element_type, like_count,
                    created_at, user_id, user_display_name, user_avatar_url,
                    my_vote, crawled_at
                ) VALUES (
                    :id, :article_id, :parent_id, :content, :element_type, :like_count,
                    :created_at, :user_id, :user_display_name, :user_avatar_url,
                    :my_vote, :crawled_at
                )
                """,
                {
                    "id": comment.get("id"),
                    "article_id": article_id,
                    "parent_id": comment.get("parent_id"),
                    "content": comment.get("content") or "",
                    "element_type": comment.get("element_type"),
                    "like_count": int(comment.get("like_count") or 0),
                    "created_at": comment.get("created_at"),
                    "user_id": user.get("id"),
                    "user_display_name": user.get("display_name"),
                    "user_avatar_url": user.get("avatar_url"),
                    "my_vote": int(comment.get("my_vote") or 0),
                    "crawled_at": crawled_at,
                },
            )
    return len(comments)


def delete_generated_pdf(relative_pdf_path: str | None) -> bool:
    if not relative_pdf_path:
        return False

    pdf_path = (MEDIA_DIR / relative_pdf_path).resolve()
    pdf_root = PDF_DIR.resolve()
    if not pdf_path.is_relative_to(pdf_root):
        return False
    if not pdf_path.exists():
        return False

    pdf_path.unlink()
    return True


def prune_old_articles_and_pdfs(cutoff_at: datetime) -> tuple[int, int]:
    cutoff_value = isoformat_utc(cutoff_at)

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, generated_pdf_path
            FROM articles
            WHERE datetime(COALESCE(approved_at, created_at, source_updated_at)) < datetime(?)
            """,
            [cutoff_value],
        ).fetchall()

        if rows:
            connection.executemany(
                "DELETE FROM articles WHERE id = ?",
                [(row["id"],) for row in rows],
            )

        referenced_pdf_paths = {
            row["generated_pdf_path"]
            for row in connection.execute(
                """
                SELECT generated_pdf_path
                FROM articles
                WHERE generated_pdf_path IS NOT NULL
                """
            ).fetchall()
        }

    deleted_pdfs = 0
    for row in rows:
        deleted_pdfs += int(delete_generated_pdf(row["generated_pdf_path"]))

    cutoff_timestamp = cutoff_at.timestamp()
    for pdf_file in PDF_DIR.glob("*.pdf"):
        relative_path = str(pdf_file.relative_to(MEDIA_DIR)).replace("\\", "/")
        if relative_path in referenced_pdf_paths:
            continue
        if pdf_file.stat().st_mtime < cutoff_timestamp:
            pdf_file.unlink(missing_ok=True)
            deleted_pdfs += 1

    return len(rows), deleted_pdfs


def crawl_articles(
    max_pages: int | None = None,
    render_scale: float = DEFAULT_RENDER_SCALE,
    crawl_window_days: int = DEFAULT_CRAWL_WINDOW_DAYS,
) -> CrawlResult:
    now = datetime.now(timezone.utc)
    cutoff_at = now - timedelta(days=crawl_window_days)
    crawled_at = isoformat_utc(now)
    existing_articles = load_existing_articles()

    with _session() as session:
        first_page_payload = fetch_article_page(session, 1)
        source_total_count = int(first_page_payload.get("count", 0))
        source_total_pages = int(first_page_payload.get("total_pages", 1))
        page_limit = min(max_pages or source_total_pages, source_total_pages)

        pages: list[list[dict[str, Any]]] = []
        fetched_pages = 0

        for page_number in range(1, page_limit + 1):
            payload = first_page_payload if page_number == 1 else fetch_article_page(session, page_number)
            page_items = payload.get("data", [])
            fetched_pages += 1

            recent_items = [item for item in page_items if is_recent_article(item, cutoff_at)]
            if recent_items:
                pages.append(recent_items)

            if not page_items or len(recent_items) != len(page_items):
                break

        fetched_articles = sum(len(items) for items in pages)
        saved_articles = 0
        regenerated_articles = 0
        rendered_pages = 0
        generated_pdfs = 0
        saved_comments = 0

        for items in pages:
            for item in items:
                try:
                    saved, regenerated, page_count, generated, comment_total = _process_article(
                        session=session,
                        list_item=item,
                        existing=existing_articles.get(item["id"]),
                        crawled_at=crawled_at,
                        render_scale=render_scale,
                    )
                except Exception:
                    continue
                saved_articles += saved
                regenerated_articles += regenerated
                rendered_pages += page_count
                generated_pdfs += generated
                saved_comments += comment_total

    pruned_articles, deleted_pdfs = prune_old_articles_and_pdfs(cutoff_at)

    return CrawlResult(
        requested_pages=page_limit,
        fetched_pages=fetched_pages,
        fetched_articles=fetched_articles,
        saved_articles=saved_articles,
        regenerated_articles=regenerated_articles,
        rendered_pages=rendered_pages,
        generated_pdfs=generated_pdfs,
        saved_comments=saved_comments,
        pruned_articles=pruned_articles,
        deleted_pdfs=deleted_pdfs,
        source_total_count=source_total_count,
        source_total_pages=source_total_pages,
        crawl_window_days=crawl_window_days,
        cutoff_at=isoformat_utc(cutoff_at),
        crawled_at=crawled_at,
    )


def _process_article(
    session: requests.Session,
    list_item: dict[str, Any],
    existing: dict[str, Any] | None,
    crawled_at: str,
    render_scale: float,
) -> tuple[int, int, int, int, int]:
    author = list_item.get("author") or {}
    page_count = int(existing.get("page_count") or 0) if existing else 0
    generated_pdf_path = existing.get("generated_pdf_path") if existing else None
    regenerated = 0
    generated = 0
    detail: dict[str, Any] | None = None

    if article_needs_regeneration(existing, list_item):
        detail = fetch_article_detail(session, list_item["id"])
        pdf_bytes = download_pdf_bytes(session, detail.get("pdf_url"))
        if pdf_bytes:
            images = render_pdf_to_images(pdf_bytes, render_scale)
            try:
                page_count = len(images)
                generated_pdf_path = build_pdf_from_images(detail["id"], images)
                regenerated = 1
                generated = 1 if generated_pdf_path else 0
            finally:
                close_images(images)

    comments = fetch_article_comments(session, list_item["id"])
    comment_count = len(comments)

    upsert_article(
        article_id=list_item["id"],
        title=list_item.get("title") or "",
        author_name=author.get("display_name"),
        tag=list_item.get("tag"),
        discipline=list_item.get("discipline"),
        zone=list_item.get("zones"),
        created_at=list_item.get("created_at"),
        approved_at=list_item.get("approved_at"),
        source_updated_at=list_item.get("updated_at"),
        rating_count=int(list_item.get("rating_count") or 0),
        avg_score=float(list_item.get("avg_score") or 0),
        comment_count=comment_count,
        page_count=page_count,
        generated_pdf_path=generated_pdf_path,
        crawled_at=crawled_at,
    )
    saved_comments = replace_article_comments(list_item["id"], comments, crawled_at)
    return 1, regenerated, page_count if regenerated else 0, generated, saved_comments


def get_article_pdf_path(generated_pdf_path: str) -> Path:
    return MEDIA_DIR / generated_pdf_path


def load_article_comments(article_id: str) -> list[dict[str, Any]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT *
            FROM article_comments
            WHERE article_id = ?
            ORDER BY datetime(created_at) ASC, id ASC
            """,
            [article_id],
        ).fetchall()
    return [hydrate_comment(row) for row in rows]


def list_article_comments(
    article_id: str,
    page: int,
    page_size: int,
) -> tuple[list[dict[str, Any]], int, int]:
    offset = (page - 1) * page_size
    with get_connection() as connection:
        total_row = connection.execute(
            "SELECT COUNT(*) AS total FROM article_comments WHERE article_id = ?",
            [article_id],
        ).fetchone()
        rows = connection.execute(
            """
            SELECT *
            FROM article_comments
            WHERE article_id = ?
            ORDER BY datetime(created_at) ASC, id ASC
            LIMIT ? OFFSET ?
            """,
            [article_id, page_size, offset],
        ).fetchall()

    total = int(total_row["total"]) if total_row else 0
    total_pages = (total + page_size - 1) // page_size if total else 0
    return [hydrate_comment(row) for row in rows], total, total_pages


def hydrate_comment(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "article_id": row["article_id"],
        "parent_id": row["parent_id"],
        "content": row["content"],
        "element_type": row["element_type"],
        "like_count": int(row["like_count"] or 0),
        "created_at": row["created_at"],
        "user": {
            "id": row["user_id"],
            "display_name": row["user_display_name"],
            "avatar_url": row["user_avatar_url"],
        },
        "my_vote": int(row["my_vote"] or 0),
    }


def render_article_page_png(
    generated_pdf_path: str,
    page_number: int,
    scale: float,
) -> tuple[bytes, int, int]:
    pdf_path = get_article_pdf_path(generated_pdf_path)
    document = fitz.open(pdf_path)
    try:
        page_index = page_number - 1
        if page_index < 0 or page_index >= document.page_count:
            raise IndexError("page out of range")
        page = document.load_page(page_index)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
        return pixmap.tobytes("png"), pixmap.width, pixmap.height
    finally:
        document.close()
