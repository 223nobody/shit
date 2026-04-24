from __future__ import annotations

from contextlib import asynccontextmanager
from threading import Lock, Thread
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response

from .crawler import (
    DEFAULT_CRAWL_WINDOW_DAYS,
    DEFAULT_RENDER_SCALE,
    crawl_articles,
    get_article_pdf_path,
    list_article_comments,
    load_article_comments,
    render_article_page_png,
)
from .content_crawler import (
    crawl_all_content,
    crawl_content_type,
    get_content,
    get_content_stats,
    list_contents,
)
from .home_crawler import (
    crawl_homepage_data,
    get_homepage_data,
    save_homepage_data,
)
from .db import get_connection, init_db


sync_lock = Lock()
startup_sync_thread: Thread | None = None
sync_state: dict[str, Any] = {
    "running": False,
    "mode": "startup_and_manual",
    "crawl_window_days": DEFAULT_CRAWL_WINDOW_DAYS,
    "last_started_at": None,
    "last_finished_at": None,
    "last_result": None,
    "last_error": None,
}


def article_page_url(article_id: str, page_number: int, scale: float = 1.0) -> str:
    return f"/api/articles/{article_id}/pages/{page_number}.png?scale={scale}"


def current_utc_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def run_sync_job(
    max_pages: int | None = None,
    render_scale: float = DEFAULT_RENDER_SCALE,
    crawl_window_days: int = DEFAULT_CRAWL_WINDOW_DAYS,
) -> dict[str, Any]:
    if not sync_lock.acquire(blocking=False):
        raise RuntimeError("sync already running")

    sync_state["running"] = True
    sync_state["last_started_at"] = current_utc_iso()
    sync_state["last_error"] = None
    sync_state["crawl_window_days"] = crawl_window_days
    try:
        # 爬取文章
        article_result = crawl_articles(
            max_pages=max_pages,
            render_scale=render_scale,
            crawl_window_days=crawl_window_days,
        )
        
        # 爬取内容 (news, questions)
        content_results = crawl_all_content(
            max_pages=max_pages,
            crawl_window_days=crawl_window_days,
        )
        
        # 爬取首页数据
        home_result = crawl_homepage_data()
        save_homepage_data(home_result)
        
        result = {
            "articles": article_result.__dict__,
            "contents": {k: v.__dict__ for k, v in content_results.items()},
            "homepage": {
                "articles_count": len(home_result.articles),
                "news_count": len(home_result.news),
                "questions_count": len(home_result.questions),
                "crawled_at": home_result.crawled_at,
            },
        }
        sync_state["last_result"] = result
        return result
    except Exception as exc:
        sync_state["last_error"] = str(exc)
        raise
    finally:
        sync_state["running"] = False
        sync_state["last_finished_at"] = current_utc_iso()
        sync_lock.release()


def run_startup_sync() -> None:
    try:
        run_sync_job()
    except Exception as e:
        print(f"Startup sync error: {e}")


def ensure_startup_sync_started() -> None:
    global startup_sync_thread
    if startup_sync_thread and startup_sync_thread.is_alive():
        return

    startup_sync_thread = Thread(target=run_startup_sync, name="shitspace-startup-sync", daemon=True)
    startup_sync_thread.start()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    ensure_startup_sync_started()
    yield


app = FastAPI(title="ShitSpace Mirror", version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/sync")
def sync_articles(
    max_pages: int | None = Query(default=None, ge=1, le=100),
    render_scale: float = Query(default=DEFAULT_RENDER_SCALE, ge=1.0, le=5.0),
    crawl_window_days: int = Query(default=DEFAULT_CRAWL_WINDOW_DAYS, ge=1, le=30),
) -> dict[str, Any]:
    try:
        result = run_sync_job(
            max_pages=max_pages,
            render_scale=render_scale,
            crawl_window_days=crawl_window_days,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"status": "success", "data": result}


@app.get("/api/articles")
def list_articles(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    zone: str | None = None,
    tag: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    conditions: list[str] = []
    params: list[Any] = []

    if zone:
        conditions.append("zone = ?")
        params.append(zone)
    if tag:
        conditions.append("tag = ?")
        params.append(tag)
    if search:
        conditions.append("(title LIKE ? OR author_name LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    offset = (page - 1) * page_size

    with get_connection() as connection:
        total_row = connection.execute(
            f"SELECT COUNT(*) AS total FROM articles {where_clause}",
            params,
        ).fetchone()
        rows = connection.execute(
            f"""
            SELECT *
            FROM articles
            {where_clause}
            ORDER BY datetime(COALESCE(approved_at, created_at)) DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()

    total = int(total_row["total"]) if total_row else 0
    total_pages = (total + page_size - 1) // page_size if total else 0
    return {
        "status": "success",
        "data": [hydrate_article_summary(row) for row in rows],
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


@app.get("/api/articles/{article_id}")
def get_article(article_id: str) -> dict[str, Any]:
    with get_connection() as connection:
        article = connection.execute(
            "SELECT * FROM articles WHERE id = ?",
            [article_id],
        ).fetchone()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    return {"status": "success", "data": hydrate_article_detail(article)}


@app.get("/api/articles/{article_id}/comments")
def get_article_comments(
    article_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict[str, Any]:
    with get_connection() as connection:
        article = connection.execute(
            "SELECT id FROM articles WHERE id = ?",
            [article_id],
        ).fetchone()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    comments, total, total_pages = list_article_comments(article_id, page, page_size)
    return {
        "status": "success",
        "data": comments,
        "count": total,
        "page": page,
        "total_pages": total_pages,
    }


@app.get("/api/articles/{article_id}/pages/{page_number}.png")
def get_article_page_image(
    article_id: str,
    page_number: int,
    scale: float = Query(default=1.6, ge=0.5, le=5.0),
) -> Response:
    with get_connection() as connection:
        article = connection.execute(
            "SELECT generated_pdf_path, page_count FROM articles WHERE id = ?",
            [article_id],
        ).fetchone()

    if not article or not article["generated_pdf_path"]:
        raise HTTPException(status_code=404, detail="Article PDF not found")

    if page_number < 1 or page_number > int(article["page_count"] or 0):
        raise HTTPException(status_code=404, detail="Page not found")

    try:
        image_bytes, _, _ = render_article_page_png(
            generated_pdf_path=article["generated_pdf_path"],
            page_number=page_number,
            scale=scale,
        )
    except IndexError as exc:
        raise HTTPException(status_code=404, detail="Page not found") from exc

    return Response(
        content=image_bytes,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=600"},
    )


@app.get("/api/articles/{article_id}/download")
def download_article_pdf(article_id: str) -> FileResponse:
    with get_connection() as connection:
        article = connection.execute(
            "SELECT title, generated_pdf_path FROM articles WHERE id = ?",
            [article_id],
        ).fetchone()

    if not article or not article["generated_pdf_path"]:
        raise HTTPException(status_code=404, detail="Generated PDF not found")

    pdf_path = get_article_pdf_path(article["generated_pdf_path"])
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Generated PDF file missing")

    safe_name = f"{article['title'] or article_id}.pdf".replace("/", "-")
    return FileResponse(pdf_path, media_type="application/pdf", filename=safe_name)


@app.get("/api/stats")
def get_stats() -> dict[str, Any]:
    with get_connection() as connection:
        overview = connection.execute(
            """
            SELECT
                COUNT(*) AS article_count,
                SUM(page_count) AS page_count,
                SUM(CASE WHEN generated_pdf_path IS NOT NULL THEN 1 ELSE 0 END) AS pdf_ready_count,
                SUM(comment_count) AS comment_count,
                MAX(crawled_at) AS latest_crawl_at
            FROM articles
            """
        ).fetchone()
        tags = connection.execute(
            """
            SELECT tag, COUNT(*) AS count
            FROM articles
            GROUP BY tag
            ORDER BY count DESC, tag ASC
            """
        ).fetchall()
        zones = connection.execute(
            """
            SELECT zone, COUNT(*) AS count
            FROM articles
            GROUP BY zone
            ORDER BY count DESC, zone ASC
            """
        ).fetchall()
        sample = connection.execute(
            """
            SELECT *
            FROM articles
            ORDER BY datetime(COALESCE(approved_at, created_at)) DESC
            LIMIT 3
            """
        ).fetchall()

    return {
        "status": "success",
        "data": {
            "overview": overview,
            "tags": tags,
            "zones": zones,
            "sample_records": [hydrate_article_summary(row) for row in sample],
            "field_format": field_format_reference(),
            "scheduler": sync_state.copy(),
        },
    }


def hydrate_article_summary(row: dict[str, Any]) -> dict[str, Any]:
    article_id = row["id"]
    page_count = int(row["page_count"] or 0)
    return {
        "id": article_id,
        "title": row["title"],
        "author_name": row["author_name"],
        "tag": row["tag"],
        "discipline": row["discipline"],
        "zone": row["zone"],
        "created_at": row["created_at"],
        "approved_at": row["approved_at"],
        "rating_count": row["rating_count"],
        "avg_score": row["avg_score"],
        "comment_count": row["comment_count"],
        "page_count": page_count,
        "cover_image_url": article_page_url(article_id, 1, 0.9) if page_count else None,
        "download_url": f"/api/articles/{article_id}/download" if row["generated_pdf_path"] else None,
        "comments_url": f"/api/articles/{article_id}/comments",
        "crawled_at": row["crawled_at"],
    }


def hydrate_article_detail(row: dict[str, Any]) -> dict[str, Any]:
    article_id = row["id"]
    page_count = int(row["page_count"] or 0)
    comments = load_article_comments(article_id)
    return {
        **hydrate_article_summary(row),
        "comments": comments,
        "pages": [
            {
                "page_number": page_number,
                "image_url": article_page_url(article_id, page_number, 1.8),
            }
            for page_number in range(1, page_count + 1)
        ],
    }


def field_format_reference() -> list[dict[str, str]]:
    return [
        {"field": "id", "type": "string", "example": "UUID"},
        {"field": "title", "type": "string", "example": "Article title"},
        {"field": "author_name", "type": "string|null", "example": "Author name"},
        {"field": "tag", "type": "string|null", "example": "meme / hardcore"},
        {"field": "discipline", "type": "string|null", "example": "interdisciplinary / social"},
        {"field": "zone", "type": "string|null", "example": "latrine"},
        {"field": "created_at", "type": "datetime string|null", "example": "2026-04-22T10:24:32.109833Z"},
        {"field": "approved_at", "type": "datetime string|null", "example": "2026-04-24T02:11:25.246668Z"},
        {"field": "source_updated_at", "type": "datetime string|null", "example": "2026-04-23T06:19:43.000890Z"},
        {"field": "rating_count", "type": "integer", "example": "16"},
        {"field": "avg_score", "type": "number", "example": "4.893"},
        {"field": "comment_count", "type": "integer", "example": "6"},
        {"field": "page_count", "type": "integer", "example": "7"},
        {"field": "cover_image_url", "type": "string|null", "example": "/api/articles/<id>/pages/1.png?scale=0.9"},
        {"field": "download_url", "type": "string|null", "example": "/api/articles/<id>/download"},
        {"field": "comments_url", "type": "string", "example": "/api/articles/<id>/comments"},
        {"field": "comments", "type": "array", "example": "[{id, content, user, created_at}]"},
        {"field": "pages", "type": "array", "example": "[{page_number, image_url}]"},
    ]


# ===== Content API (News, Questions, RealShit) =====

VALID_CONTENT_TYPES = {"news", "questions", "realshit"}


@app.get("/api/content/{content_type}")
def list_content_api(
    content_type: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    tag: str | None = None,
    search: str | None = None,
) -> dict[str, Any]:
    """列出指定类型的内容 (news, questions, realshit)"""
    if content_type not in VALID_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid content type. Must be one of: {VALID_CONTENT_TYPES}")
    
    items, total = list_contents(
        content_type=content_type,
        page=page,
        page_size=page_size,
        tag=tag,
        search=search,
    )
    
    total_pages = (total + page_size - 1) // page_size if total else 0
    
    return {
        "status": "success",
        "data": items,
        "meta": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    }


@app.get("/api/content/{content_type}/{content_id}")
def get_content_api(content_type: str, content_id: str) -> dict[str, Any]:
    """获取单个内容详情"""
    if content_type not in VALID_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid content type. Must be one of: {VALID_CONTENT_TYPES}")
    
    content = get_content(content_id)
    
    if not content or content.get("content_type") != content_type:
        raise HTTPException(status_code=404, detail="Content not found")
    
    return {"status": "success", "data": content}





@app.get("/api/content/stats")
def content_stats_api() -> dict[str, Any]:
    """获取内容统计"""
    stats = get_content_stats()
    return {"status": "success", "data": stats}


@app.get("/api/homepage")
def homepage_api() -> dict[str, Any]:
    """获取首页数据"""
    data = get_homepage_data()
    if not data:
        # 如果没有数据，实时爬取
        result = crawl_homepage_data()
        save_homepage_data(result)
        data = {
            "editorial": result.editorial,
            "articles": result.articles,
            "news": result.news,
            "questions": result.questions,
        }
    return {"status": "success", "data": data}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
