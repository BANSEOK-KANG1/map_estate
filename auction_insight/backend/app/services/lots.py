"""Lot serialization and search helpers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuctionLot, Region
from app.schemas import (
    InsightScore,
    LegalRiskOut,
    LotDetail,
    LotSummary,
    MarketCompare,
    PoiOut,
    ScheduleOut,
    SearchRequest,
)
from app.services.kakao import POI_CATEGORIES
from app.services.score import combine_insight

SOURCE_LABELS = {"onbid": "공매", "court": "경매"}
CATEGORY_LABELS = {v[0]: v[1] for v in POI_CATEGORIES.values()}


def _scores_from_lot(lot: AuctionLot) -> InsightScore:
    return InsightScore(
        discount_vs_appraisal=lot.discount_vs_appraisal,
        discount_vs_market=lot.discount_vs_market,
        infra=lot.infra_score,
        urgency=lot.urgency_score,
        total=lot.total_score,
    )


def _market_confidence(sample_count: int) -> str:
    if sample_count >= 20:
        return "high"
    if sample_count >= 8:
        return "medium"
    return "low"


def _market_from_lot(lot: AuctionLot) -> MarketCompare:
    note = (lot.market_note or "").strip()
    if not note:
        if lot.market_sample_count < 3:
            note = "인근 실거래 표본이 부족합니다. 시세 비교는 참고용입니다."
        elif lot.dong:
            note = f"{lot.dong} 인근·유사면적 실거래 중위가 (표본 {lot.market_sample_count}건)"
        else:
            note = f"유사면적 실거래 중위가 (표본 {lot.market_sample_count}건)"
    return MarketCompare(
        median_manwon=lot.market_median_manwon,
        pyeong_manwon=lot.market_pyeong_manwon,
        sample_count=lot.market_sample_count,
        note=note,
        confidence=_market_confidence(lot.market_sample_count),
    )


def _days_left(lot: AuctionLot) -> int | None:
    if lot.bid_end_at is None:
        return None
    delta = lot.bid_end_at - datetime.utcnow()
    return max(0, delta.days)


def _highlights(lot: AuctionLot) -> list[str]:
    tags: list[str] = []
    if lot.fail_count > 0:
        tags.append(f"유찰 {lot.fail_count}회")
    days = _days_left(lot)
    if days is not None and days <= 7:
        tags.append(f"D-{days}" if days > 0 else "마감")
    if lot.discount_vs_market is not None and lot.discount_vs_market >= 0.2:
        tags.append(f"시세대비 {int(lot.discount_vs_market * 100)}%↓")
    elif lot.discount_vs_appraisal is not None and lot.discount_vs_appraisal >= 0.25:
        tags.append(f"감정대비 {int(lot.discount_vs_appraisal * 100)}%↓")
    if lot.nearest_station:
        walk = f" 도보{lot.station_walk_minutes}분" if lot.station_walk_minutes else ""
        tags.append(f"{lot.nearest_station}{walk}")
    if lot.market_sample_count and lot.market_sample_count < 8:
        tags.append("시세표본 적음")
    return tags[:4]


def _thumbnail(lot: AuctionLot) -> str | None:
    try:
        urls = json.loads(lot.photo_urls or "[]")
        if urls:
            return urls[0]
    except json.JSONDecodeError:
        pass
    return None


def to_summary(lot: AuctionLot, region_name: str | None = None) -> LotSummary:
    name = region_name
    if name is None and lot.region is not None:
        name = lot.region.name
    return LotSummary(
        id=lot.id,
        source=lot.source,
        source_label=SOURCE_LABELS.get(lot.source, lot.source),
        external_id=lot.external_id,
        case_no=lot.case_no,
        court_name=lot.court_name or "",
        title=lot.title or lot.address,
        usage=lot.usage,
        address=lot.address,
        region_code=lot.region_code,
        region_name=name,
        dong=lot.dong,
        exclusive_area=lot.exclusive_area,
        build_year=lot.build_year,
        floor_info=lot.floor_info or "",
        appraisal_manwon=lot.appraisal_manwon,
        min_bid_manwon=lot.min_bid_manwon,
        fail_count=lot.fail_count,
        status=lot.status,
        bid_end_at=lot.bid_end_at,
        sale_date=lot.sale_date,
        days_left=_days_left(lot),
        lat=lot.lat,
        lng=lot.lng,
        source_url=lot.source_url,
        thumbnail_url=_thumbnail(lot),
        nearest_station=lot.nearest_station or None,
        station_line=lot.station_line or None,
        station_walk_minutes=lot.station_walk_minutes,
        scores=_scores_from_lot(lot),
        market=_market_from_lot(lot),
        highlights=_highlights(lot),
    )


def _legal_from_lot(lot: AuctionLot) -> LegalRiskOut | None:
    raw = (lot.detail_json or "").strip()
    if not raw or raw == "{}":
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return LegalRiskOut(
        org_name=str(data.get("org_name") or ""),
        eviction_target=str(data.get("eviction_target") or ""),
        etc_note=str(data.get("etc_note") or ""),
        utilization_note=str(data.get("utilization_note") or ""),
        location_note=str(data.get("location_note") or ""),
        risk_flags=list(data.get("risk_flags") or []),
        notes=list(data.get("notes") or []),
        lease_count=int(data.get("lease_count") or 0),
        occupy_count=int(data.get("occupy_count") or 0),
        registry_count=int(data.get("registry_count") or 0),
        appraisals=list(data.get("appraisals") or []),
        bid_rounds=list(data.get("bid_rounds") or []),
        gaps=list(data.get("gaps") or []),
        bid_info_status=data.get("bid_info_status"),
    )


def to_detail(lot: AuctionLot) -> LotDetail:
    base = to_summary(lot)
    try:
        photos = json.loads(lot.photo_urls or "[]")
    except json.JSONDecodeError:
        photos = []
    schedules = [
        ScheduleOut(
            round_no=s.round_no,
            sale_date=s.sale_date,
            min_bid_manwon=s.min_bid_manwon,
            result=s.result,
            note=s.note,
        )
        for s in sorted(lot.schedules, key=lambda x: x.round_no)
    ]
    pois: list[PoiOut] = []
    for p in lot.pois:
        try:
            places = json.loads(p.payload_json or "[]")
        except json.JSONDecodeError:
            places = []
        pois.append(
            PoiOut(
                category=p.category,
                category_label=CATEGORY_LABELS.get(p.category, p.category),
                count=p.count,
                nearest_distance_m=p.nearest_distance_m,
                places=places,
            )
        )
    return LotDetail(
        **base.model_dump(),
        land_area=lot.land_area,
        description=lot.description,
        photo_urls=photos,
        schedules=schedules,
        pois=sorted(pois, key=lambda x: x.category),
        legal=_legal_from_lot(lot),
        bid_start_at=lot.bid_start_at,
    )


async def search_lots(session: AsyncSession, req: SearchRequest) -> tuple[int, list[LotSummary]]:
    q = select(AuctionLot).options(selectinload(AuctionLot.region))
    count_q = select(func.count(AuctionLot.id))

    def apply_filters(stmt: Any) -> Any:
        if req.sources:
            stmt = stmt.where(AuctionLot.source.in_(req.sources))
        if req.region_codes:
            stmt = stmt.where(AuctionLot.region_code.in_(req.region_codes))
        if req.min_price_manwon is not None:
            stmt = stmt.where(AuctionLot.min_bid_manwon >= req.min_price_manwon)
        if req.max_price_manwon is not None:
            stmt = stmt.where(AuctionLot.min_bid_manwon <= req.max_price_manwon)
        if req.min_fail_count is not None:
            stmt = stmt.where(AuctionLot.fail_count >= req.min_fail_count)
        if req.max_fail_count is not None:
            stmt = stmt.where(AuctionLot.fail_count <= req.max_fail_count)
        if req.status:
            stmt = stmt.where(AuctionLot.status == req.status)
        if req.bid_end_before is not None:
            stmt = stmt.where(AuctionLot.bid_end_at <= req.bid_end_before)
        if req.bid_end_after is not None:
            stmt = stmt.where(AuctionLot.bid_end_at >= req.bid_end_after)
        if req.north is not None and req.south is not None:
            stmt = stmt.where(AuctionLot.lat <= req.north, AuctionLot.lat >= req.south)
        if req.east is not None and req.west is not None:
            stmt = stmt.where(AuctionLot.lng <= req.east, AuctionLot.lng >= req.west)
        if req.q:
            like = f"%{req.q}%"
            stmt = stmt.where(
                (AuctionLot.title.ilike(like))
                | (AuctionLot.address.ilike(like))
                | (AuctionLot.case_no.ilike(like))
            )
        return stmt

    q = apply_filters(q)
    count_q = apply_filters(count_q)
    total = (await session.execute(count_q)).scalar_one()
    q = (
        q.order_by(AuctionLot.total_score.desc().nullslast(), AuctionLot.bid_end_at.asc().nullslast())
        .offset(req.offset)
        .limit(min(req.limit, 200))
    )
    rows = (await session.execute(q)).scalars().all()
    return total, [to_summary(r) for r in rows]


async def get_lot(session: AsyncSession, lot_id: int) -> AuctionLot | None:
    result = await session.execute(
        select(AuctionLot)
        .options(
            selectinload(AuctionLot.region),
            selectinload(AuctionLot.schedules),
            selectinload(AuctionLot.pois),
        )
        .where(AuctionLot.id == lot_id)
    )
    return result.scalar_one_or_none()


async def seed_regions(session: AsyncSession) -> int:
    from app.data.regions import ALL_REGIONS

    added = 0
    for r in ALL_REGIONS:
        existing = await session.get(Region, r["code"])
        if existing is None:
            session.add(Region(code=r["code"], name=r["name"], sido=r["sido"]))
            added += 1
    await session.commit()
    return added


def match_region_code(address: str) -> str | None:
    """Best-effort match of address to region code by name substring."""
    from app.data.regions import ALL_REGIONS

    # Narrow by sido first so 서울/인천 중구 등이 섞이지 않음
    sido_hits = [
        r
        for r in ALL_REGIONS
        if r["sido"] in address or r["sido"][:2] in address
    ]
    pool = sido_hits if sido_hits else ALL_REGIONS
    sorted_regions = sorted(pool, key=lambda x: len(x["name"]), reverse=True)
    for r in sorted_regions:
        if r["name"] in address:
            return r["code"]
        short = r["name"].split()[-1] if " " in r["name"] else r["name"]
        if short in address and short.endswith(("구", "시", "군")):
            return r["code"]
    return None


__all__ = [
    "to_summary",
    "to_detail",
    "search_lots",
    "get_lot",
    "seed_regions",
    "match_region_code",
    "combine_insight",
]
