"""
Content Crawler for News, Questions, and RealShit
爬取 S.H.*.T Space 的 news、questions、realshit 内容
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .db import get_connection

SOURCE_BASE_URL = "https://shitspace.xyz"
DEFAULT_TIMEOUT = 30
DEFAULT_CRAWL_WINDOW_DAYS = 7
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

CONTENT_TYPES = {
    "news": "/api/news/",
    "questions": "/api/questions/",
}


@dataclass
class ContentCrawlResult:
    content_type: str
    fetched_items: int
    saved_items: int
    saved_comments: int
    crawled_at: str


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Referer": f"{SOURCE_BASE_URL}/",
    })
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


def fetch_content_list(session: requests.Session, content_type: str, page: int = 1) -> dict[str, Any]:
    """获取内容列表"""
    endpoint = f"{SOURCE_BASE_URL}{CONTENT_TYPES[content_type]}"
    response = session.get(endpoint, params={"page": page}, timeout=DEFAULT_TIMEOUT)
    return _parse_json(response)


def fetch_content_detail(session: requests.Session, content_type: str, content_id: str) -> dict[str, Any]:
    """获取内容详情"""
    endpoint = f"{SOURCE_BASE_URL}{CONTENT_TYPES[content_type]}{content_id}"
    response = session.get(endpoint, timeout=DEFAULT_TIMEOUT)
    return _parse_json(response)


def fetch_content_comments(session: requests.Session, content_type: str, content_id: str) -> list[dict[str, Any]]:
    """获取内容评论"""
    comments = []
    page = 1
    total_pages = 1
    
    while page <= total_pages:
        try:
            endpoint = f"{SOURCE_BASE_URL}{CONTENT_TYPES[content_type]}{content_id}/comments"
            response = session.get(endpoint, params={"page": page, "page_size": 100}, timeout=DEFAULT_TIMEOUT)
            if response.status_code == 404:
                # 评论接口不存在或没有评论
                break
            payload = _parse_json(response)
            comments.extend(payload.get("data", []))
            total_pages = max(int(payload.get("total_pages") or 1), 1)
            page += 1
        except Exception as e:
            print(f"Warning: Failed to fetch comments for {content_type}/{content_id}: {e}")
            break
    
    return comments


def upsert_content(
    content_id: str,
    content_type: str,
    title: str,
    content: str | None,
    author_name: str | None,
    author_avatar: str | None,
    tag: str | None,
    status: str | None,
    created_at: str | None,
    updated_at: str | None,
    rating_count: int,
    avg_score: float,
    comment_count: int,
    view_count: int,
    like_count: int,
    source_url: str | None,
    crawled_at: str,
) -> None:
    """插入或更新内容"""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO contents (
                id, content_type, title, content, author_name, author_avatar,
                tag, status, created_at, updated_at, rating_count, avg_score,
                comment_count, view_count, like_count, source_url, crawled_at
            ) VALUES (
                :id, :content_type, :title, :content, :author_name, :author_avatar,
                :tag, :status, :created_at, :updated_at, :rating_count, :avg_score,
                :comment_count, :view_count, :like_count, :source_url, :crawled_at
            )
            ON CONFLICT(id) DO UPDATE SET
                title = excluded.title,
                content = excluded.content,
                author_name = excluded.author_name,
                author_avatar = excluded.author_avatar,
                tag = excluded.tag,
                status = excluded.status,
                created_at = excluded.created_at,
                updated_at = excluded.updated_at,
                rating_count = excluded.rating_count,
                avg_score = excluded.avg_score,
                comment_count = excluded.comment_count,
                view_count = excluded.view_count,
                like_count = excluded.like_count,
                source_url = excluded.source_url,
                crawled_at = excluded.crawled_at
            """,
            {
                "id": content_id,
                "content_type": content_type,
                "title": title,
                "content": content,
                "author_name": author_name,
                "author_avatar": author_avatar,
                "tag": tag,
                "status": status,
                "created_at": created_at,
                "updated_at": updated_at,
                "rating_count": rating_count,
                "avg_score": avg_score,
                "comment_count": comment_count,
                "view_count": view_count,
                "like_count": like_count,
                "source_url": source_url,
                "crawled_at": crawled_at,
            },
        )
        connection.commit()


def replace_content_comments(
    content_id: str,
    content_type: str,
    comments: list[dict[str, Any]],
    crawled_at: str,
) -> int:
    """替换内容评论"""
    with get_connection() as connection:
        connection.execute(
            "DELETE FROM content_comments WHERE content_id = ? AND content_type = ?",
            [content_id, content_type]
        )
        for comment in comments:
            user = comment.get("user") or {}
            connection.execute(
                """
                INSERT INTO content_comments (
                    id, content_id, content_type, parent_id, content,
                    like_count, created_at, user_id, user_display_name,
                    user_avatar_url, crawled_at
                ) VALUES (
                    :id, :content_id, :content_type, :parent_id, :content,
                    :like_count, :created_at, :user_id, :user_display_name,
                    :user_avatar_url, :crawled_at
                )
                """,
                {
                    "id": comment.get("id") or f"{content_id}-comment-{hash(str(comment))}",
                    "content_id": content_id,
                    "content_type": content_type,
                    "parent_id": comment.get("parent_id"),
                    "content": comment.get("content") or "",
                    "like_count": int(comment.get("like_count") or 0),
                    "created_at": comment.get("created_at"),
                    "user_id": user.get("id"),
                    "user_display_name": user.get("display_name"),
                    "user_avatar_url": user.get("avatar_url"),
                    "crawled_at": crawled_at,
                },
            )
        connection.commit()
    return len(comments)


def crawl_content_type(
    content_type: str,
    max_pages: int | None = None,
    crawl_window_days: int = DEFAULT_CRAWL_WINDOW_DAYS,
) -> ContentCrawlResult:
    """爬取指定类型的内容"""
    now = datetime.now(timezone.utc)
    cutoff_at = now - timedelta(days=crawl_window_days)
    crawled_at = now.isoformat()
    
    with _session() as session:
        # 获取第一页
        first_page = fetch_content_list(session, content_type, 1)
        total_pages = max(int(first_page.get("total_pages") or 1), 1)
        page_limit = min(max_pages or total_pages, total_pages)
        
        all_items = []
        fetched_pages = 0
        
        for page_num in range(1, page_limit + 1):
            if page_num == 1:
                page_data = first_page
            else:
                page_data = fetch_content_list(session, content_type, page_num)
            
            items = page_data.get("data", [])
            fetched_pages += 1
            
            # 过滤近期内容
            for item in items:
                item_date = item.get("created_at") or item.get("updated_at")
                if item_date:
                    try:
                        item_datetime = datetime.fromisoformat(item_date.replace("Z", "+00:00"))
                        if item_datetime >= cutoff_at:
                            all_items.append(item)
                    except ValueError:
                        all_items.append(item)  # 日期解析失败也保留
                else:
                    all_items.append(item)
        
        # 保存内容和评论
        saved_items = 0
        saved_comments = 0
        
        for item in all_items:
            try:
                content_id = item.get("id")
                if not content_id:
                    continue
                
                # 获取详情（如果有更多字段）
                try:
                    detail = fetch_content_detail(session, content_type, content_id)
                    item.update(detail.get("data", {}))
                except Exception:
                    pass  # 使用列表中的数据
                
                # 获取评论
                comments = fetch_content_comments(session, content_type, content_id)
                
                author = item.get("author") or {}
                
                # 处理不同内容类型的字段差异
                # news 使用 summary, questions 使用 content
                content_text = item.get("content") or item.get("body") or item.get("summary") or item.get("description") or ""
                
                # 获取评论数（优先使用 API 返回的 comment_count，否则使用实际获取的评论数）
                api_comment_count = item.get("comment_count")
                actual_comment_count = len(comments)
                comment_count = api_comment_count if api_comment_count is not None else actual_comment_count
                
                upsert_content(
                    content_id=content_id,
                    content_type=content_type,
                    title=item.get("title") or "无标题",
                    content=content_text,
                    author_name=author.get("display_name"),
                    author_avatar=author.get("avatar_url"),
                    tag=item.get("tag"),
                    status=item.get("status"),
                    created_at=item.get("created_at"),
                    updated_at=item.get("updated_at"),
                    rating_count=int(item.get("rating_count") or 0),
                    avg_score=float(item.get("avg_score") or 0),
                    comment_count=comment_count,
                    view_count=int(item.get("view_count") or 0),
                    like_count=int(item.get("like_count") or 0),
                    source_url=f"{SOURCE_BASE_URL}/{content_type}/{content_id}",
                    crawled_at=crawled_at,
                )
                
                saved_comments += replace_content_comments(content_id, content_type, comments, crawled_at)
                saved_items += 1
                
            except Exception as e:
                print(f"Error processing {content_type} item {item.get('id')}: {e}")
                continue
    
    return ContentCrawlResult(
        content_type=content_type,
        fetched_items=len(all_items),
        saved_items=saved_items,
        saved_comments=saved_comments,
        crawled_at=crawled_at,
    )


def crawl_all_content(
    max_pages: int | None = None,
    crawl_window_days: int = DEFAULT_CRAWL_WINDOW_DAYS,
) -> dict[str, ContentCrawlResult]:
    """爬取所有内容类型"""
    results = {}
    for content_type in CONTENT_TYPES.keys():
        try:
            result = crawl_content_type(content_type, max_pages, crawl_window_days)
            results[content_type] = result
        except Exception as e:
            print(f"Error crawling {content_type}: {e}")
            results[content_type] = ContentCrawlResult(
                content_type=content_type,
                fetched_items=0,
                saved_items=0,
                saved_comments=0,
                crawled_at=datetime.now(timezone.utc).isoformat(),
            )
    return results


def list_contents(
    content_type: str,
    page: int = 1,
    page_size: int = 10,
    tag: str | None = None,
    search: str | None = None,
) -> tuple[list[dict[str, Any]], int]:
    """列出内容"""
    conditions = ["content_type = ?"]
    params = [content_type]
    
    if tag:
        conditions.append("tag = ?")
        params.append(tag)
    if search:
        conditions.append("(title LIKE ? OR content LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])
    
    where_clause = f"WHERE {' AND '.join(conditions)}"
    offset = (page - 1) * page_size
    
    with get_connection() as connection:
        total_row = connection.execute(
            f"SELECT COUNT(*) AS total FROM contents {where_clause}",
            params,
        ).fetchone()
        
        rows = connection.execute(
            f"""
            SELECT * FROM contents
            {where_clause}
            ORDER BY datetime(COALESCE(updated_at, created_at)) DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
    
    total = int(total_row["total"]) if total_row else 0
    return [hydrate_content(row) for row in rows], total


def get_content(content_id: str) -> dict[str, Any] | None:
    """获取单个内容"""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM contents WHERE id = ?",
            [content_id],
        ).fetchone()
    
    if not row:
        return None
    
    content = hydrate_content(row)
    content["comments"] = load_content_comments(content_id)
    return content


def load_content_comments(content_id: str) -> list[dict[str, Any]]:
    """加载内容评论"""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT * FROM content_comments
            WHERE content_id = ?
            ORDER BY datetime(created_at) ASC, id ASC
            """,
            [content_id],
        ).fetchall()
    
    return [hydrate_content_comment(row) for row in rows]


def hydrate_content(row: dict[str, Any]) -> dict[str, Any]:
    """转换内容为API格式"""
    return {
        "id": row["id"],
        "content_type": row["content_type"],
        "title": row["title"],
        "content": row["content"],
        "author": {
            "name": row["author_name"],
            "avatar": row["author_avatar"],
        },
        "tag": row["tag"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "rating_count": row["rating_count"],
        "avg_score": row["avg_score"],
        "comment_count": row["comment_count"],
        "view_count": row["view_count"],
        "like_count": row["like_count"],
        "source_url": row["source_url"],
        "crawled_at": row["crawled_at"],
    }


def hydrate_content_comment(row: dict[str, Any]) -> dict[str, Any]:
    """转换评论为API格式"""
    return {
        "id": row["id"],
        "content_id": row["content_id"],
        "content_type": row["content_type"],
        "parent_id": row["parent_id"],
        "content": row["content"],
        "like_count": row["like_count"],
        "created_at": row["created_at"],
        "user": {
            "id": row["user_id"],
            "display_name": row["user_display_name"],
            "avatar_url": row["user_avatar_url"],
        },
    }


def get_content_stats() -> dict[str, Any]:
    """获取内容统计"""
    with get_connection() as connection:
        overview = connection.execute(
            """
            SELECT
                content_type,
                COUNT(*) AS count,
                SUM(comment_count) AS total_comments,
                SUM(view_count) AS total_views,
                SUM(like_count) AS total_likes
            FROM contents
            GROUP BY content_type
            """
        ).fetchall()
        
        latest_crawl = connection.execute(
            "SELECT MAX(crawled_at) AS latest FROM contents"
        ).fetchone()
    
    return {
        "by_type": {row["content_type"]: dict(row) for row in overview},
        "latest_crawl_at": latest_crawl["latest"] if latest_crawl else None,
    }
