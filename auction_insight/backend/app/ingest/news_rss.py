"""개발호재 뉴스 RSS — 제목·링크만 수집 (본문 미수집)."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus, urlparse
from xml.etree.ElementTree import Element

import httpx
from defusedxml import ElementTree as ET
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import IngestRun
from app.services.insights import external_id_hash, upsert_insight

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AuctionInsight/1.0; +https://github.com/local/auction_insight)"
    ),
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

# (시도단축, 검색어)
NEWS_QUERIES: list[tuple[str, str]] = [
    ("서울", "서울 재개발"),
    ("서울", "서울 정비구역"),
    ("서울", "서울 도시개발"),
    ("경기", "경기 재개발"),
    ("경기", "경기 정비구역"),
    ("경기", "경기 도시개발"),
    ("인천", "인천 재개발"),
    ("인천", "인천 정비구역"),
    ("인천", "인천 도시개발"),
]


def _google_news_rss_url(query: str) -> str:
    q = quote_plus(query)
    return f"https://news.google.com/rss/search?q={q}&hl=ko&gl=KR&ceid=KR:ko"


def _text(el: Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text.strip()


def _find_child(parent: Element, names: tuple[str, ...]) -> Element | None:
    for child in list(parent):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in names:
            return child
    return None


def _parse_pub_date(raw: str) -> datetime | None:
    s = (raw or "").strip()
    if not s:
        return None
    try:
        return parsedate_to_datetime(s).replace(tzinfo=None)
    except (TypeError, ValueError, IndexError):
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(s.replace("+00:00", "Z"), fmt.replace("%z", "Z") if "Z" in fmt else fmt)
            return dt.replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _publisher_from_title(title: str, link: str) -> str:
    # Google News titles often end with " - 매체명"
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()[:64]
    host = urlparse(link).netloc
    return host.replace("www.", "")[:64] if host else "뉴스"


def parse_rss_items(xml_text: str) -> list[dict[str, str]]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return []
    items: list[dict[str, str]] = []
    for node in root.iter():
        tag = node.tag.split("}")[-1] if "}" in node.tag else node.tag
        if tag != "item":
            continue
        title_el = _find_child(node, ("title",))
        link_el = _find_child(node, ("link",))
        pub_el = _find_child(node, ("pubDate", "published", "updated"))
        desc_el = _find_child(node, ("description", "summary"))
        title = _text(title_el)
        link = _text(link_el)
        if not title or not link:
            continue
        items.append(
            {
                "title": title,
                "link": link,
                "pubDate": _text(pub_el),
                "description": _text(desc_el)[:280],
            }
        )
    return items


async def _fetch_rss(client: httpx.AsyncClient, url: str) -> list[dict[str, str]]:
    res = await client.get(url)
    res.raise_for_status()
    return parse_rss_items(res.text)


async def ingest_news_rss(
    db: AsyncSession,
    settings: Settings,  # noqa: ARG001 — signature parity with other ingest
    *,
    per_feed_limit: int = 8,
) -> IngestRun:
    upserted = 0
    feeds = 0
    err_msg = ""
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        ) as client:
            for sido, query in NEWS_QUERIES:
                url = _google_news_rss_url(query)
                try:
                    items = await _fetch_rss(client, url)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("news rss fetch failed %s: %s", query, exc)
                    continue
                feeds += 1
                for item in items[: max(1, per_feed_limit)]:
                    link = item["link"]
                    title = item["title"]
                    ext = external_id_hash(link)
                    pub = _parse_pub_date(item.get("pubDate") or "")
                    publisher = _publisher_from_title(title, link)
                    # Strip publisher suffix from display title when present
                    display = title
                    if publisher and display.endswith(f" - {publisher}"):
                        display = display[: -(len(publisher) + 3)].strip()
                    await upsert_insight(
                        db,
                        source="news_rss",
                        external_id=ext,
                        category="개발호재",
                        sido=sido,
                        sgg="",
                        title=display[:500],
                        summary=(item.get("description") or "")[:280],
                        source_url=link[:1000],
                        publisher=publisher,
                        published_at=pub,
                        data_as_of=None,
                        detail={"query": query},
                    )
                    upserted += 1
                await db.commit()
                await asyncio.sleep(0.2)
        status = "ok"
        message = f"news_rss upserted={upserted} feeds={feeds}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("news rss ingest failed")
        err_msg = str(exc)[:400]
        status = "error"
        message = f"news_rss failed: {err_msg}"
        await db.rollback()

    run = IngestRun(
        source="news_rss",
        status=status,
        lot_count=upserted,
        message=message,
        finished_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()
    return run
