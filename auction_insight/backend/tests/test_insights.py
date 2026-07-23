"""호재 인사이트 — 정규화·RSS 파싱·목록 필터."""

import asyncio
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db import Base
from app.ingest.news_rss import parse_rss_items
from app.ingest.redevelopment import _row_to_fields
from app.services.insights import (
    list_insights,
    normalize_sido,
    seed_demo_insights,
    upsert_insight,
)


def test_normalize_sido():
    assert normalize_sido("서울특별시") == "서울"
    assert normalize_sido("경기도") == "경기"
    assert normalize_sido("인천광역시") == "인천"
    assert normalize_sido("부산광역시") is None


def test_redev_row_filters_non_mvp_sido():
    assert (
        _row_to_fields(
            {
                "ZONE_NM": "해운대구역",
                "CTPV_NM": "부산광역시",
                "SGG_NM": "해운대구",
                "PRGRS_STP_CN": "조합설립",
            }
        )
        is None
    )


def test_redev_row_maps_seoul():
    fields = _row_to_fields(
        {
            "ZONE_NM": "성수전략정비구역",
            "CTPV_NM": "서울특별시",
            "SGG_NM": "성동구",
            "PRGRS_STP_CN": "사업시행인가",
            "HH_CNT": "2400",
            "DATA_CRTR_YMD": "20251201",
        }
    )
    assert fields is not None
    assert fields["sido"] == "서울"
    assert fields["sgg"] == "성동구"
    assert "사업시행인가" in fields["summary"]
    assert fields["data_as_of"] == date(2025, 12, 1)


def test_parse_rss_items_title_link():
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
      <item>
        <title>서울 재개발 추진 - 매일경제</title>
        <link>https://example.com/a</link>
        <pubDate>Mon, 20 Jul 2026 09:00:00 GMT</pubDate>
        <description>요약만</description>
      </item>
    </channel></rss>"""
    items = parse_rss_items(xml)
    assert len(items) == 1
    assert items[0]["title"].startswith("서울")
    assert items[0]["link"] == "https://example.com/a"


def test_parse_csv_insights_incheon():
    from app.ingest.redevelopment import parse_csv_insights

    csv_text = (
        "구명,구 역 명,위치,면적(제곱미터),사업유형,진행단계\n"
        "중구,경동율목,경동 40번지 일원,34218,재개발,조합설립인가\n"
    )
    rows = parse_csv_insights(
        csv_text, default_sido="인천", source_label="인천 정비"
    )
    assert len(rows) == 1
    assert rows[0]["sido"] == "인천"
    assert rows[0]["zone"] == "경동율목"
    assert "조합설립인가" in rows[0]["summary"]


def test_list_insights_sido_filter():
    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session_factory = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            await upsert_insight(
                db,
                source="redev_std",
                external_id="a",
                category="재개발정비",
                sido="서울",
                title="A",
            )
            await upsert_insight(
                db,
                source="news_rss",
                external_id="b",
                category="개발호재",
                sido="경기",
                title="B",
            )
            await db.commit()
            total, rows = await list_insights(db, sido="서울특별시")
            assert total == 1
            assert rows[0].title == "A"
            total2, rows2 = await list_insights(db, category="개발호재")
            assert total2 == 1
            assert rows2[0].sido == "경기"

    asyncio.run(_run())


def test_seed_demo_insights():
    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        session_factory = async_sessionmaker(
            engine, expire_on_commit=False, class_=AsyncSession
        )
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with session_factory() as db:
            n = await seed_demo_insights(db)
            assert n >= 6
            total, _ = await list_insights(db)
            assert total >= 6

    asyncio.run(_run())
