"""MarketInsight 조회·정규화·데모 시드."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MarketInsight
from app.schemas import MarketInsightOut

SIDO_SHORT = ("서울", "경기", "인천")

SOURCE_LABELS = {
    "redev_std": "정비사업(공공)",
    "redev_csv": "정비사업(지자체)",
    "news_rss": "뉴스",
    "demo": "데모",
}


def normalize_sido(raw: str) -> str | None:
    """시도명을 MVP 단축명(서울/경기/인천)으로 정규화. 대상 외면 None."""
    s = (raw or "").strip()
    if not s:
        return None
    if s.startswith("서울"):
        return "서울"
    if s.startswith("경기"):
        return "경기"
    if s.startswith("인천"):
        return "인천"
    return None


def sido_from_region_filter(sido_full: str | None) -> str | None:
    """Flutter RegionQuickBar 전체명 → 단축명."""
    if not sido_full:
        return None
    return normalize_sido(sido_full)


def external_id_hash(*parts: str) -> str:
    raw = "|".join(p.strip() for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:40]


def to_out(row: MarketInsight) -> MarketInsightOut:
    return MarketInsightOut(
        id=row.id,
        source=row.source,
        source_label=SOURCE_LABELS.get(row.source, row.source),
        category=row.category,
        sido=row.sido,
        sgg=row.sgg or "",
        title=row.title,
        summary=row.summary or "",
        source_url=row.source_url or "",
        publisher=row.publisher or "",
        published_at=row.published_at,
        data_as_of=row.data_as_of,
    )


async def upsert_insight(
    db: AsyncSession,
    *,
    source: str,
    external_id: str,
    category: str,
    sido: str,
    title: str,
    summary: str = "",
    sgg: str = "",
    source_url: str = "",
    publisher: str = "",
    published_at: datetime | None = None,
    data_as_of: date | None = None,
    detail: dict | None = None,
) -> MarketInsight:
    result = await db.execute(
        select(MarketInsight).where(
            MarketInsight.source == source,
            MarketInsight.external_id == external_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        row = MarketInsight(source=source, external_id=external_id)
        db.add(row)
    row.category = category
    row.sido = sido
    row.sgg = sgg or ""
    row.title = title
    row.summary = summary or ""
    row.source_url = source_url or ""
    row.publisher = publisher or ""
    row.published_at = published_at
    row.data_as_of = data_as_of
    row.detail_json = json.dumps(detail or {}, ensure_ascii=False)
    row.updated_at = datetime.utcnow()
    return row


async def list_insights(
    db: AsyncSession,
    *,
    sido: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> tuple[int, list[MarketInsight]]:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    stmt = select(MarketInsight)
    count_stmt = select(func.count(MarketInsight.id))
    if sido:
        short = normalize_sido(sido) or sido
        stmt = stmt.where(MarketInsight.sido == short)
        count_stmt = count_stmt.where(MarketInsight.sido == short)
    if category and category != "전체":
        stmt = stmt.where(MarketInsight.category == category)
        count_stmt = count_stmt.where(MarketInsight.category == category)
    if q and q.strip():
        like = f"%{q.strip()}%"
        filt = or_(
            MarketInsight.title.ilike(like),
            MarketInsight.summary.ilike(like),
            MarketInsight.sgg.ilike(like),
        )
        stmt = stmt.where(filt)
        count_stmt = count_stmt.where(filt)

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(
                MarketInsight.published_at.desc().nullslast(),
                MarketInsight.data_as_of.desc().nullslast(),
                MarketInsight.id.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
    ).scalars().all()
    return total, list(rows)


DEMO_INSIGHTS: list[dict] = [
    {
        "source": "demo",
        "external_id": "demo-redev-seoul-1",
        "category": "재개발정비",
        "sido": "서울",
        "sgg": "성동구",
        "title": "성수전략정비구역 (데모)",
        "summary": "진행단계: 사업시행인가 · 세대수 약 2,400",
        "source_url": "https://www.data.go.kr/data/15155703/standard.do",
        "publisher": "데모",
        "data_as_of": date(2025, 12, 1),
    },
    {
        "source": "demo",
        "external_id": "demo-redev-gyeonggi-1",
        "category": "재개발정비",
        "sido": "경기",
        "sgg": "성남시 수정구",
        "title": "수정구 일대 재개발 (데모)",
        "summary": "진행단계: 조합설립인가 · 세대수 약 1,100",
        "source_url": "https://www.data.go.kr/data/15155703/standard.do",
        "publisher": "데모",
        "data_as_of": date(2025, 11, 15),
    },
    {
        "source": "demo",
        "external_id": "demo-redev-incheon-1",
        "category": "재개발정비",
        "sido": "인천",
        "sgg": "미추홀구",
        "title": "미추홀 주거환경개선 (데모)",
        "summary": "진행단계: 정비구역지정 · 세대수 약 800",
        "source_url": "https://www.data.go.kr/data/15155703/standard.do",
        "publisher": "데모",
        "data_as_of": date(2025, 10, 20),
    },
    {
        "source": "demo",
        "external_id": "demo-news-seoul-1",
        "category": "개발호재",
        "sido": "서울",
        "sgg": "",
        "title": "서울 도심 정비구역 추진 동향 (데모 링크)",
        "summary": "뉴스 제목·링크만 제공 · 본문 미수집",
        "source_url": (
            "https://news.google.com/search?q=%EC%84%9C%EC%9A%B8+%EC%9E%AC%EA%B0%9C%EB%B0%9C"
            "&hl=ko&gl=KR&ceid=KR:ko"
        ),
        "publisher": "Google News",
        "published_at": datetime(2026, 7, 20, 9, 0),
    },
    {
        "source": "demo",
        "external_id": "demo-news-gyeonggi-1",
        "category": "개발호재",
        "sido": "경기",
        "sgg": "",
        "title": "경기 도시개발·정비 관련 보도 (데모 링크)",
        "summary": "뉴스 제목·링크만 제공 · 본문 미수집",
        "source_url": (
            "https://news.google.com/search?q=%EA%B2%BD%EA%B8%B0+%EC%A0%95%EB%B9%84%EA%B5%AC%EC%97%AD"
            "&hl=ko&gl=KR&ceid=KR:ko"
        ),
        "publisher": "Google News",
        "published_at": datetime(2026, 7, 18, 11, 0),
    },
    {
        "source": "demo",
        "external_id": "demo-news-incheon-1",
        "category": "개발호재",
        "sido": "인천",
        "sgg": "",
        "title": "인천 재개발·도시개발 보도 (데모 링크)",
        "summary": "뉴스 제목·링크만 제공 · 본문 미수집",
        "source_url": (
            "https://news.google.com/search?q=%EC%9D%B8%EC%B2%9C+%EB%8F%84%EC%8B%9C%EA%B0%9C%EB%B0%9C"
            "&hl=ko&gl=KR&ceid=KR:ko"
        ),
        "publisher": "Google News",
        "published_at": datetime(2026, 7, 15, 14, 0),
    },
]


async def seed_demo_insights(db: AsyncSession) -> int:
    n = 0
    for raw in DEMO_INSIGHTS:
        await upsert_insight(
            db,
            source=raw["source"],
            external_id=raw["external_id"],
            category=raw["category"],
            sido=raw["sido"],
            sgg=raw.get("sgg") or "",
            title=raw["title"],
            summary=raw.get("summary") or "",
            source_url=raw.get("source_url") or "",
            publisher=raw.get("publisher") or "",
            published_at=raw.get("published_at"),
            data_as_of=raw.get("data_as_of"),
            detail={"demo": True},
        )
        n += 1
    await db.commit()
    return n
