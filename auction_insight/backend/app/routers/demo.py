"""데모 시드 — 풍부한 경·공매 카탈로그."""

from __future__ import annotations

import json
from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select

from app.config import Settings, get_settings
from app.data.demo_catalog import demo_catalog
from app.db import Base, SessionLocal, engine
from app.models import AuctionLot, AuctionSchedule, PoiCache
from app.schemas import IngestResponse
from app.services.enrich import enrich_lots
from app.services.insights import seed_demo_insights
from app.services.lots import match_region_code, seed_regions
from app.services.score import apply_lot_scores

router = APIRouter(prefix="/demo", tags=["demo"])


async def _reset_tables() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


async def _upsert_from_catalog(session, raw: dict) -> AuctionLot:
    result = await session.execute(
        select(AuctionLot).where(
            AuctionLot.source == raw["source"],
            AuctionLot.external_id == raw["external_id"],
        )
    )
    lot = result.scalar_one_or_none()
    if lot is None:
        lot = AuctionLot(source=raw["source"], external_id=raw["external_id"])
        session.add(lot)

    lot.case_no = raw["case_no"]
    lot.court_name = raw.get("court_name") or ""
    lot.title = raw["title"]
    lot.usage = raw["usage"]
    lot.address = raw["address"]
    lot.region_code = match_region_code(raw["address"])
    lot.dong = raw.get("dong") or ""
    lot.exclusive_area = raw.get("exclusive_area")
    lot.land_area = raw.get("land_area")
    lot.build_year = raw.get("build_year")
    lot.floor_info = raw.get("floor") or ""
    lot.appraisal_manwon = raw["appraisal_manwon"]
    lot.min_bid_manwon = raw["min_bid_manwon"]
    lot.fail_count = raw["fail_count"]
    lot.status = raw.get("status") or "active"
    lot.bid_end_at = raw["bid_end_at"]
    lot.sale_date = raw["sale_date"]
    lot.source_url = raw.get("source_url") or ""
    lot.description = raw.get("description") or ""
    lot.lat = raw.get("lat")
    lot.lng = raw.get("lng")
    lot.geocoded_at = datetime.utcnow() if lot.lat else None
    lot.photo_urls = "[]"
    lot.nearest_station = raw.get("nearest_station") or ""
    lot.station_line = raw.get("station_line") or ""
    lot.station_walk_minutes = raw.get("station_walk_minutes")
    lot.market_median_manwon = raw.get("market_median_manwon")
    lot.market_sample_count = int(raw.get("market_sample_count") or 0)
    lot.market_note = raw.get("market_note") or ""
    if lot.exclusive_area and lot.market_median_manwon and lot.exclusive_area > 0:
        lot.market_pyeong_manwon = round(
            lot.market_median_manwon / (lot.exclusive_area / 3.3058), 1
        )

    lot.infra_score = float(raw.get("infra") or 60.0)
    apply_lot_scores(lot)

    await session.flush()

    for s in raw.get("schedules") or []:
        round_no = int(s["round_no"])
        existing = await session.execute(
            select(AuctionSchedule).where(
                AuctionSchedule.lot_id == lot.id,
                AuctionSchedule.round_no == round_no,
            )
        )
        sched = existing.scalar_one_or_none()
        if sched is None:
            sched = AuctionSchedule(lot_id=lot.id, round_no=round_no)
            session.add(sched)
        sale = s.get("sale_date")
        sched.sale_date = date.fromisoformat(sale) if isinstance(sale, str) else sale
        sched.min_bid_manwon = s.get("min_bid_manwon")
        sched.result = s.get("result") or ""
        sched.note = s.get("note") or ""

    existing_pois = (
        await session.execute(select(PoiCache).where(PoiCache.lot_id == lot.id))
    ).scalars().all()
    for p in existing_pois:
        await session.delete(p)

    for cat, _label, count, nearest, places in raw.get("pois") or []:
        session.add(
            PoiCache(
                lot_id=lot.id,
                category=cat,
                count=count,
                nearest_distance_m=float(nearest) if nearest is not None else None,
                payload_json=json.dumps(places, ensure_ascii=False),
                fetched_at=datetime.utcnow(),
            )
        )

    return lot


@router.post("/seed", response_model=IngestResponse)
async def seed_demo(
    enrich: bool = False,
    reset: bool = True,
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    if reset:
        await _reset_tables()

    async with SessionLocal() as session:
        await seed_regions(session)
        count = 0
        for raw in demo_catalog():
            await _upsert_from_catalog(session, raw)
            count += 1
        await session.commit()
        insight_n = await seed_demo_insights(session)
        if enrich:
            lots = (await session.execute(select(AuctionLot))).scalars().all()
            await enrich_lots(session, settings, list(lots))
        return IngestResponse(
            status="ok",
            lot_count=count,
            message=(
                f"demo seed complete ({count} lots, {insight_n} insights, "
                f"reset={reset})"
            ),
        )
