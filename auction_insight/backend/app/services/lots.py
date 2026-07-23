"""Lot serialization and search helpers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import AuctionLot, Region
from app.schemas import (
    InsightScore,
    LegalInfoRow,
    LegalRiskOut,
    LegalRowField,
    ChecklistItem,
    LotDetail,
    LotSummary,
    MarketCompare,
    PoiOut,
    ScheduleOut,
    SearchRequest,
)
from app.services.kakao import POI_CATEGORIES
from app.services.score import apply_lot_scores

SOURCE_LABELS = {"onbid": "공매", "court": "경매"}
CATEGORY_LABELS = {v[0]: v[1] for v in POI_CATEGORIES.values()}


def _scores_from_lot(lot: AuctionLot) -> InsightScore:
    from app.services.score import score_from_fields

    # Live recompute so algorithm changes show immediately in list/detail.
    return score_from_fields(
        min_bid_manwon=lot.min_bid_manwon,
        appraisal_manwon=lot.appraisal_manwon,
        market_median_manwon=lot.market_median_manwon,
        infra_score=lot.infra_score,
        bid_end_at=lot.bid_end_at,
        fail_count=lot.fail_count,
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


def _risk_flags_brief(lot: AuctionLot) -> list[str]:
    raw = (lot.detail_json or "").strip()
    if not raw or raw == "{}":
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, dict):
        return []
    out: list[str] = []
    for flag in data.get("risk_flags") or []:
        text = str(flag)
        if any(
            k in text
            for k in (
                "유치권",
                "법정지상권",
                "가처분",
                "가등기",
                "분묘",
                "위반건축",
                "임차권",
            )
        ):
            out.append(text)
        if len(out) >= 3:
            break
    return out


def _highlights(lot: AuctionLot) -> list[str]:
    tags: list[str] = []
    if lot.fail_count > 0:
        tags.append(f"유찰 {lot.fail_count}회")
    days = _days_left(lot)
    if days is not None and days <= 7:
        tags.append(f"D-{days}" if days > 0 else "마감")
    if lot.discount_vs_appraisal is not None and lot.discount_vs_appraisal >= 0.15:
        tags.append(f"감정 {int(lot.discount_vs_appraisal * 100)}%↓")
    if lot.discount_vs_market is not None and lot.discount_vs_market >= 0.15:
        tags.append(f"시세 {int(lot.discount_vs_market * 100)}%↓")
    if lot.nearest_station:
        walk = f" 도보{lot.station_walk_minutes}분" if lot.station_walk_minutes else ""
        tags.append(f"{lot.nearest_station}{walk}")
    if lot.market_sample_count and lot.market_sample_count < 8:
        tags.append("시세표본 적음")
    return tags[:5]


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
        risk_flags=_risk_flags_brief(lot),
    )


def _as_legal_rows(raw_rows: Any, raw_items: Any, kind: str) -> list[LegalInfoRow]:
    from app.ingest.onbid_detail import _normalize_rows

    if isinstance(raw_rows, list) and raw_rows:
        out: list[LegalInfoRow] = []
        for row in raw_rows[:20]:
            if not isinstance(row, dict):
                continue
            fields = [
                LegalRowField(
                    key=str(f.get("key") or ""),
                    label=str(f.get("label") or ""),
                    value=str(f.get("value") or ""),
                )
                for f in (row.get("fields") or [])
                if isinstance(f, dict)
            ]
            out.append(
                LegalInfoRow(
                    title=str(row.get("title") or ""),
                    subtitle=str(row.get("subtitle") or ""),
                    fields=fields,
                )
            )
        if out:
            return out
    if isinstance(raw_items, list) and raw_items:
        return [
            LegalInfoRow(
                title=str(r.get("title") or ""),
                subtitle=str(r.get("subtitle") or ""),
                fields=[
                    LegalRowField(
                        key=str(f.get("key") or ""),
                        label=str(f.get("label") or ""),
                        value=str(f.get("value") or ""),
                    )
                    for f in (r.get("fields") or [])
                    if isinstance(f, dict)
                ],
            )
            for r in _normalize_rows(raw_items[:20], kind)
        ]
    return []


def _beginner_checklist(lot: AuctionLot, data: dict[str, Any]) -> list[ChecklistItem]:
    appraisals = data.get("appraisals") or []
    lease_n = int(data.get("lease_count") or 0)
    occupy_n = int(data.get("occupy_count") or 0)
    registry_n = int(data.get("registry_count") or 0)
    flags = [str(f) for f in (data.get("risk_flags") or [])]
    risky = any(k in " ".join(flags) for k in ("유치권", "법정지상권", "가처분", "가등기", "분묘"))

    items = [
        ChecklistItem(
            id="iros",
            title="등기부등본 열람 (갑구·을구)",
            detail="소유권·근저당·가압류·가처분·임차권등기를 인터넷등기소에서 확인하세요. 온비드 목록만으로 최신 등기를 대체할 수 없습니다.",
            priority=1,
            status="required",
            link="https://www.iros.go.kr",
        ),
        ChecklistItem(
            id="onbid",
            title="온비드 원문 공고·특약 확인",
            detail="명도책임·부대조건·매수자격·이용현황은 원문 기준으로 최종 확인합니다.",
            priority=1,
            status="ready" if lot.source_url else "required",
            link=lot.source_url or None,
        ),
        ChecklistItem(
            id="appraisal",
            title="감정평가서 PDF 확인",
            detail="건물 하자·토지 이용제한·평가 기준일이 가격에 영향을 줍니다.",
            priority=1,
            status="ready" if appraisals else "required",
        ),
        ChecklistItem(
            id="lease",
            title="임대차·대항력·보증금",
            detail=(
                f"온비드 임대차 {lease_n}건 표시. "
                "대항력·확정일자·우선변제는 등기·주민센터·현장으로 교차 확인하세요."
            ),
            priority=1,
            status="warn" if lease_n > 0 else "todo",
        ),
        ChecklistItem(
            id="occupy",
            title="점유·명도 리스크",
            detail=(
                f"점유관계 {occupy_n}건. "
                f"명도책임: {data.get('eviction_target') or '원문 확인'}."
            ),
            priority=1,
            status="warn" if occupy_n > 0 or data.get("eviction_target") else "todo",
        ),
        ChecklistItem(
            id="registry_list",
            title="온비드 등기·우선변제 목록",
            detail=(
                f"공고에 등기관련 {registry_n}건이 있습니다. "
                "말소기준권리·인수/말소 판단은 등기부등본 + 전문가 확인이 필요합니다."
            ),
            priority=1,
            status="warn" if registry_n > 0 else "todo",
        ),
        ChecklistItem(
            id="site",
            title="현장 확인",
            detail="실사용·불법건축·누수·주차·단지 규칙을 직접 확인하세요.",
            priority=2,
            status="todo",
        ),
        ChecklistItem(
            id="price",
            title="가격 안전마진",
            detail=(
                f"유찰 {lot.fail_count}회 · 감정 대비 할인 "
                f"{(lot.discount_vs_appraisal * 100):.0f}%"
                if lot.discount_vs_appraisal is not None
                else f"유찰 {lot.fail_count}회 · 시세·감정가와 최저가를 비교하세요."
            ),
            priority=2,
            status="tip",
        ),
    ]
    if risky:
        items.insert(
            0,
            ChecklistItem(
                id="redflag",
                title="고위험 키워드 감지",
                detail="유치권·법정지상권·가처분 등이 기타사항 텍스트에 언급됩니다. 초보는 보류를 권장합니다.",
                priority=1,
                status="warn",
            ),
        )
    return items


def _strategy_tips(lot: AuctionLot, data: dict[str, Any]) -> list[str]:
    tips = [
        "초보 기본: ‘싸 보인다’보다 ‘인수할 권리가 무엇인가’를 먼저 보세요.",
        "필수 3종: ①등기부등본 ②감정평가서 ③온비드 원문 특약.",
        "유찰 횟수만으로 저평가라고 단정하지 마세요. 권리·하자·접근성이 원인일 수 있습니다.",
    ]
    if lot.fail_count >= 2:
        tips.append("유찰 2회+: 왜 안 팔렸는지(권리·명도·입지·가격)를 가설로 적어보고 검증하세요.")
    if int(data.get("lease_count") or 0) > 0:
        tips.append("임대차가 있으면 보증금 반환·대항력 여부를 등기와 함께 확인하세요.")
    if any("유치권" in str(f) or "법정지상권" in str(f) for f in (data.get("risk_flags") or [])):
        tips.append("유치권·법정지상권 신호가 있으면 초보 단계에서는 패스하는 편이 안전합니다.")
    if lot.discount_vs_appraisal is not None and lot.discount_vs_appraisal >= 0.3:
        tips.append("감정가 대비 할인율이 크면 기회일 수도, 함정일 수도 있습니다. 권리 점검 후 입찰가를 정하세요.")
    tips.append("입찰 전날 등기·공고를 한 번 더 새로고침하고, 자금·명도 비용을 합산한 총원가로 판단하세요.")
    return tips


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
        lease_rows=_as_legal_rows(data.get("lease_rows"), data.get("leases"), "lease"),
        occupy_rows=_as_legal_rows(data.get("occupy_rows"), data.get("occupy"), "occupy"),
        registry_rows=_as_legal_rows(
            data.get("registry_rows"), data.get("registry"), "registry"
        ),
        checklist=_beginner_checklist(lot, data),
        strategy_tips=_strategy_tips(lot, data),
        iros_url=str(data.get("iros_url") or "https://www.iros.go.kr"),
        onbid_notice=str(
            data.get("onbid_notice")
            or "온비드 목록은 공고 시점 요약입니다. 입찰 직전 원문·등기를 다시 확인하세요."
        ),
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


async def rescore_lots(
    session: AsyncSession,
    *,
    only_missing: bool = False,
    limit: int = 8000,
) -> int:
    """Persist screening scores from price/deadline/fail fields (no external API)."""
    stmt = select(AuctionLot).order_by(AuctionLot.id.asc()).limit(limit)
    if only_missing:
        stmt = select(AuctionLot).where(AuctionLot.total_score.is_(None)).limit(limit)
    rows = (await session.execute(stmt)).scalars().all()
    for lot in rows:
        apply_lot_scores(lot)
    if rows:
        await session.commit()
    return len(rows)


async def search_lots(session: AsyncSession, req: SearchRequest) -> tuple[int, list[LotSummary]]:
    # Ensure sort-by-score works even before Kakao/MOLIT enrich.
    missing = (
        await session.execute(
            select(func.count(AuctionLot.id)).where(AuctionLot.total_score.is_(None))
        )
    ).scalar_one()
    if missing:
        await rescore_lots(session, only_missing=True)
    elif not getattr(search_lots, "_full_rescore_done", False):
        # Once per process after deploy: rewrite totals with new algorithm.
        await rescore_lots(session, only_missing=False)
        setattr(search_lots, "_full_rescore_done", True)
    q = select(AuctionLot).options(selectinload(AuctionLot.region))
    count_q = select(func.count(AuctionLot.id))

    def apply_filters(stmt: Any) -> Any:
        if req.sources:
            stmt = stmt.where(AuctionLot.source.in_(req.sources))
        if req.region_codes:
            stmt = stmt.where(AuctionLot.region_code.in_(req.region_codes))
        if req.usages:
            usage_filters = [
                AuctionLot.usage.ilike(f"%{u.strip()}%")
                for u in req.usages
                if u and u.strip()
            ]
            if usage_filters:
                stmt = stmt.where(or_(*usage_filters))
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

    sort = (req.sort or "score").strip().lower()
    if sort == "deadline":
        order = (
            AuctionLot.bid_end_at.asc().nullslast(),
            AuctionLot.lat.isnot(None).desc(),
            AuctionLot.total_score.desc().nullslast(),
        )
    elif sort == "discount":
        order = (
            AuctionLot.discount_vs_appraisal.desc().nullslast(),
            AuctionLot.lat.isnot(None).desc(),
            AuctionLot.bid_end_at.asc().nullslast(),
        )
    else:
        # score (default): prefer mapped lots, then insight score
        order = (
            AuctionLot.lat.isnot(None).desc(),
            AuctionLot.total_score.desc().nullslast(),
            AuctionLot.bid_end_at.asc().nullslast(),
        )

    q = q.order_by(*order).offset(req.offset).limit(min(req.limit, 200))
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


async def get_lot_by_key(
    session: AsyncSession,
    source: str,
    external_id: str,
) -> AuctionLot | None:
    result = await session.execute(
        select(AuctionLot)
        .options(
            selectinload(AuctionLot.region),
            selectinload(AuctionLot.schedules),
            selectinload(AuctionLot.pois),
        )
        .where(
            AuctionLot.source == source,
            AuctionLot.external_id == external_id,
        )
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
    "get_lot_by_key",
    "seed_regions",
    "match_region_code",
    "combine_insight",
]
