"""
Homepage data crawler for S.H.*.T Space
爬取首页需要的各类数据
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .db import get_connection

SOURCE_BASE_URL = "https://shitspace.xyz"
DEFAULT_TIMEOUT = 30
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# Editorial/Manifesto content (static for now, can be fetched from API if available)
EDITORIAL_CONTENT = {
    "title": "A Manifesto for Academic Decentralization",
    "title_cn": "全民学术人宣言",
    "subtitle": "EDITORIAL / 社论",
    "content": """《S.H.*.T》试图回答一个问题：如果把编辑部的权力交还给社区，学术评价会变得更好还是更糟？

在这里，没有学术大佬，没有权威审稿。每一篇来稿，每一篇评论都将经历一场近乎残酷的"进化论"，好的思想会自己浮上来，坏的自然沉底。""",
    "featured_image": None,
}


@dataclass
class HomeDataResult:
    articles: list[dict[str, Any]]
    news: list[dict[str, Any]]
    questions: list[dict[str, Any]]
    editorial: dict[str, Any]
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


def fetch_latest_articles(session: requests.Session, limit: int = 5) -> list[dict[str, Any]]:
    """获取最新文章"""
    try:
        endpoint = f"{SOURCE_BASE_URL}/api/articles/"
        response = session.get(endpoint, params={"page": 1, "page_size": limit}, timeout=DEFAULT_TIMEOUT)
        payload = _parse_json(response)
        items = payload.get("data", [])
        
        # 简化数据
        return [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "tag": item.get("tag"),
                "discipline": item.get("discipline"),
                "author": item.get("author", {}),
                "rating_count": item.get("rating_count", 0),
                "avg_score": item.get("avg_score", 0),
                "comment_count": item.get("comment_count", 0),
                "created_at": item.get("created_at"),
                "zones": item.get("zones"),
            }
            for item in items[:limit]
        ]
    except Exception as e:
        print(f"Error fetching articles: {e}")
        return []


def fetch_latest_news(session: requests.Session, limit: int = 3) -> list[dict[str, Any]]:
    """获取最新新闻"""
    try:
        endpoint = f"{SOURCE_BASE_URL}/api/news/"
        response = session.get(endpoint, params={"page": 1, "page_size": limit}, timeout=DEFAULT_TIMEOUT)
        payload = _parse_json(response)
        items = payload.get("data", [])
        
        return [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "summary": item.get("summary"),
                "topic": item.get("topic"),
                "created_at": item.get("created_at"),
            }
            for item in items[:limit]
        ]
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


def fetch_latest_questions(session: requests.Session, limit: int = 3) -> list[dict[str, Any]]:
    """获取最新问题"""
    try:
        endpoint = f"{SOURCE_BASE_URL}/api/questions/"
        response = session.get(endpoint, params={"page": 1, "page_size": limit}, timeout=DEFAULT_TIMEOUT)
        payload = _parse_json(response)
        items = payload.get("data", [])
        
        return [
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "content": item.get("content", "")[:200] + "..." if len(item.get("content", "")) > 200 else item.get("content", ""),
                "tag": item.get("tag"),
                "author": item.get("author", {}),
                "rating_count": item.get("rating_count", 0),
                "avg_score": item.get("avg_score", 0),
                "comment_count": item.get("comment_count", 0),
                "created_at": item.get("created_at"),
            }
            for item in items[:limit]
        ]
    except Exception as e:
        print(f"Error fetching questions: {e}")
        return []


def crawl_homepage_data() -> HomeDataResult:
    """爬取首页所有数据"""
    crawled_at = datetime.now(timezone.utc).isoformat()
    
    with _session() as session:
        articles = fetch_latest_articles(session, limit=5)
        news = fetch_latest_news(session, limit=3)
        questions = fetch_latest_questions(session, limit=3)
    
    return HomeDataResult(
        articles=articles,
        news=news,
        questions=questions,
        editorial=EDITORIAL_CONTENT,
        crawled_at=crawled_at,
    )


def save_homepage_data(result: HomeDataResult) -> None:
    """保存首页数据到数据库"""
    with get_connection() as connection:
        # 保存 editorial
        connection.execute(
            """
            INSERT INTO homepage_data (key, data_type, content, updated_at)
            VALUES ('editorial', 'editorial', :content, :updated_at)
            ON CONFLICT(key) DO UPDATE SET
                content = excluded.content,
                updated_at = excluded.updated_at
            """,
            {
                "content": str(result.editorial),
                "updated_at": result.crawled_at,
            },
        )
        
        # 保存 articles
        connection.execute(
            """
            INSERT INTO homepage_data (key, data_type, content, updated_at)
            VALUES ('articles', 'articles', :content, :updated_at)
            ON CONFLICT(key) DO UPDATE SET
                content = excluded.content,
                updated_at = excluded.updated_at
            """,
            {
                "content": str(result.articles),
                "updated_at": result.crawled_at,
            },
        )
        
        # 保存 news
        connection.execute(
            """
            INSERT INTO homepage_data (key, data_type, content, updated_at)
            VALUES ('news', 'news', :content, :updated_at)
            ON CONFLICT(key) DO UPDATE SET
                content = excluded.content,
                updated_at = excluded.updated_at
            """,
            {
                "content": str(result.news),
                "updated_at": result.crawled_at,
            },
        )
        
        # 保存 questions
        connection.execute(
            """
            INSERT INTO homepage_data (key, data_type, content, updated_at)
            VALUES ('questions', 'questions', :content, :updated_at)
            ON CONFLICT(key) DO UPDATE SET
                content = excluded.content,
                updated_at = excluded.updated_at
            """,
            {
                "content": str(result.questions),
                "updated_at": result.crawled_at,
            },
        )
        
        connection.commit()


def get_homepage_data() -> dict[str, Any]:
    """获取首页数据"""
    with get_connection() as connection:
        rows = connection.execute(
            "SELECT key, content FROM homepage_data"
        ).fetchall()
    
    result = {}
    for row in rows:
        key = row["key"]
        content = row["content"]
        try:
            import ast
            result[key] = ast.literal_eval(content)
        except:
            result[key] = content
    
    return result
