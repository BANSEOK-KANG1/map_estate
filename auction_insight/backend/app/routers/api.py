from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.ingest.news_rss import ingest_news_rss
from app.ingest.onbid import ingest_onbid
from app.ingest.redevelopment import ingest_redevelopment
from app.models import (
    AuctionLot,
    AuctionSchedule,
    MarketInsight,
    NearbyTrade,
    PoiCache,
    Region,
)
from app.schemas import (
    EnrichRequest,
    HealthOut,
    IngestRequest,
    IngestResponse,
    InsightsResponse,
    LotDetail,
    RegionOut,
    SearchRequest,
    SearchResponse,
)
from app.services.enrich import enrich_lot, enrich_lots
from app.services.insights import list_insights, seed_demo_insights, to_out
from app.services.lots import (
    get_lot,
    get_lot_by_key,
    rescore_lots,
    search_lots,
    seed_regions,
    to_detail,
)

router = APIRouter(tags=["api"])

DEMO_EXTERNAL_PREFIXES = ("court-202", "onbid-demo-")


def _is_demo_external_id(external_id: str) -> bool:
    return any(external_id.startswith(p) for p in DEMO_EXTERNAL_PREFIXES)


async def _clear_demo_lots(db: AsyncSession) -> int:
    rows = (await db.execute(select(AuctionLot))).scalars().all()
    demo_ids = [r.id for r in rows if _is_demo_external_id(r.external_id)]
    if not demo_ids:
        return 0
    await db.execute(delete(PoiCache).where(PoiCache.lot_id.in_(demo_ids)))
    await db.execute(delete(NearbyTrade).where(NearbyTrade.lot_id.in_(demo_ids)))
    await db.execute(delete(AuctionSchedule).where(AuctionSchedule.lot_id.in_(demo_ids)))
    await db.execute(delete(AuctionLot).where(AuctionLot.id.in_(demo_ids)))
    await db.commit()
    return len(demo_ids)


async def _clear_onbid_lots(db: AsyncSession) -> int:
    rows = (
        await db.execute(select(AuctionLot.id).where(AuctionLot.source == "onbid"))
    ).scalars().all()
    ids = list(rows)
    if not ids:
        return 0
    await db.execute(delete(PoiCache).where(PoiCache.lot_id.in_(ids)))
    await db.execute(delete(NearbyTrade).where(NearbyTrade.lot_id.in_(ids)))
    await db.execute(delete(AuctionSchedule).where(AuctionSchedule.lot_id.in_(ids)))
    await db.execute(delete(AuctionLot).where(AuctionLot.id.in_(ids)))
    await db.commit()
    return len(ids)


@router.get("/health", response_model=HealthOut)
async def health(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> HealthOut:
    total = (await db.execute(select(func.count(AuctionLot.id)))).scalar_one()
    onbid_n = (
        await db.execute(
            select(func.count(AuctionLot.id)).where(AuctionLot.source == "onbid")
        )
    ).scalar_one()
    court_n = (
        await db.execute(
            select(func.count(AuctionLot.id)).where(AuctionLot.source == "court")
        )
    ).scalar_one()
    demo_n = (
        await db.execute(
            select(func.count(AuctionLot.id)).where(
                or_(
                    AuctionLot.external_id.startswith("court-202"),
                    AuctionLot.external_id.startswith("onbid-demo-"),
                )
            )
        )
    ).scalar_one()
    real_n = total - demo_n
    if real_n > 0 and demo_n == 0:
        mode = "real"
    elif real_n > 0 and demo_n > 0:
        mode = "mixed"
    else:
        mode = "demo"

    analysis_meta: dict = {}
    try:
        from app.analysis.models import AuctionItem
        from app.analysis.storage import document_store_status

        analysis_n = (
            await db.execute(select(func.count(AuctionItem.id)))
        ).scalar_one()
        analysis_meta = {
            "item_count": analysis_n,
            "doc_store": document_store_status(),
        }
    except Exception:  # noqa: BLE001
        analysis_meta = {"item_count": 0, "doc_store": {"kind": "unknown"}}

    insight_n = (
        await db.execute(select(func.count(MarketInsight.id)))
    ).scalar_one()

    return HealthOut(
        status="ok",
        mode=mode,
        lot_count=total,
        onbid_lot_count=onbid_n,
        court_lot_count=court_n,
        demo_lot_count=demo_n,
        insight_count=insight_n,
        keys={
            "onbid": bool(settings.onbid_service_key),
            "molit": bool(settings.molit_service_key),
            "kakao": bool(settings.kakao_rest_key),
            "redev": bool(settings.redev_service_key),
        },
        analysis=analysis_meta,
    )


@router.get("/insights", response_model=InsightsResponse)
async def get_insights(
    sido: str | None = None,
    category: str | None = None,
    q: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
) -> InsightsResponse:
    total, rows = await list_insights(
        db, sido=sido, category=category, q=q, limit=limit, offset=offset
    )
    return InsightsResponse(total=total, items=[to_out(r) for r in rows])


@router.post("/ingest/insights", response_model=IngestResponse)
async def ingest_insights_endpoint(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """정비사업 OpenAPI + 뉴스 RSS 링크 갱신."""
    messages: list[str] = []
    total = 0
    statuses: list[str] = []

    redev_run = await ingest_redevelopment(db, settings)
    messages.append(redev_run.message)
    total += redev_run.lot_count
    statuses.append(redev_run.status)

    news_run = await ingest_news_rss(db, settings)
    messages.append(news_run.message)
    total += news_run.lot_count
    statuses.append(news_run.status)

    # 키 없고 정비 실패면 데모로 UI 유지
    if total == 0 and "error" not in statuses:
        seeded = await seed_demo_insights(db)
        if seeded:
            total = seeded
            messages.append(f"demo insights seeded={seeded}")
            statuses.append("ok")

    if all(s == "error" for s in statuses):
        status = "error"
    elif total == 0:
        status = "empty"
    elif "error" in statuses:
        status = "partial"
    else:
        status = "ok"

    return IngestResponse(
        status=status,
        lot_count=total,
        message=" | ".join(m for m in messages if m),
    )


@router.post("/enrich", response_model=IngestResponse)
async def enrich_existing(
    req: EnrichRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """Re-enrich existing lots with Molit market (and Kakao POI if keyed)."""
    limit = max(1, min(req.limit, 200))
    lots = await _select_lots_for_enrich(db, req, limit)
    if not lots:
        return IngestResponse(status="empty", lot_count=0, message="no lots")
    n = await enrich_lots(
        db,
        settings,
        list(lots),
        fetch_market=req.fetch_market,
        fetch_pois=req.fetch_pois and bool(settings.kakao_rest_key),
        fetch_detail=req.fetch_detail and bool(settings.onbid_service_key),
    )
    with_coords = sum(1 for lot in lots if lot.lat is not None and lot.lng is not None)
    return IngestResponse(
        status="ok",
        lot_count=len(lots),
        enriched=n,
        message=(
            f"enriched {n} lots · coords={with_coords}/{len(lots)} "
            f"(market={req.fetch_market}, "
            f"pois={bool(settings.kakao_rest_key) and req.fetch_pois}, "
            f"detail={bool(settings.onbid_service_key) and req.fetch_detail}, "
            f"missing_coords_only={req.missing_coords_only}, "
            f"balance_by_sido={req.balance_by_sido})"
        ),
    )


@router.post("/rescore", response_model=IngestResponse)
async def rescore_existing(
    db: AsyncSession = Depends(get_db),
    only_missing: bool = False,
) -> IngestResponse:
    """Recompute screening scores from appraisal/market/deadline/fail (no external API)."""
    n = await rescore_lots(db, only_missing=only_missing)
    return IngestResponse(
        status="ok",
        lot_count=n,
        enriched=n,
        message=f"rescored {n} lots (only_missing={only_missing})",
    )


async def _select_lots_for_enrich(
    db: AsyncSession,
    req: EnrichRequest,
    limit: int,
) -> list[AuctionLot]:
    """Pick lots for enrich; optionally balance Seoul/Gyeonggi/Incheon."""
    from app.data.regions import GYEONGGI_REGIONS, INCHEON_REGIONS, SEOUL_REGIONS

    def base_stmt():
        stmt = select(AuctionLot)
        if req.missing_coords_only:
            stmt = stmt.where(AuctionLot.lat.is_(None))
        if req.region_codes:
            stmt = stmt.where(AuctionLot.region_code.in_(req.region_codes))
        return stmt.order_by(
            AuctionLot.bid_end_at.asc().nullslast(),
            AuctionLot.id.asc(),
        )

    if not req.balance_by_sido or req.region_codes:
        return list((await db.execute(base_stmt().limit(limit))).scalars().all())

    groups = [
        [r["code"] for r in SEOUL_REGIONS],
        [r["code"] for r in GYEONGGI_REGIONS],
        [r["code"] for r in INCHEON_REGIONS],
    ]
    per = max(1, limit // len(groups))
    picked: list[AuctionLot] = []
    seen: set[int] = set()
    for codes in groups:
        stmt = select(AuctionLot)
        if req.missing_coords_only:
            stmt = stmt.where(AuctionLot.lat.is_(None))
        stmt = (
            stmt.where(AuctionLot.region_code.in_(codes))
            .order_by(AuctionLot.bid_end_at.asc().nullslast(), AuctionLot.id.asc())
            .limit(per)
        )
        for lot in (await db.execute(stmt)).scalars().all():
            if lot.id not in seen:
                picked.append(lot)
                seen.add(lot.id)
    if len(picked) < limit:
        for lot in (await db.execute(base_stmt().limit(limit))).scalars().all():
            if lot.id not in seen:
                picked.append(lot)
                seen.add(lot.id)
            if len(picked) >= limit:
                break
    return picked[:limit]


@router.get("/regions", response_model=list[RegionOut])
async def list_regions(db: AsyncSession = Depends(get_db)) -> list[RegionOut]:
    await seed_regions(db)
    rows = (await db.execute(select(Region).order_by(Region.sido, Region.name))).scalars().all()
    # Prefer 서울 → 경기 → 인천 (alphabetical puts 경기 first)
    sido_rank = {"서울특별시": 0, "경기도": 1, "인천광역시": 2}
    rows = sorted(rows, key=lambda r: (sido_rank.get(r.sido, 99), r.name))
    return [RegionOut(code=r.code, name=r.name, sido=r.sido) for r in rows]


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)) -> SearchResponse:
    total, items = await search_lots(db, req)
    return SearchResponse(total=total, items=items)


@router.get("/lots/by-key", response_model=LotDetail)
async def lot_detail_by_key(
    source: str,
    external_id: str,
    enrich: bool = False,
    fetch_detail: bool = False,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LotDetail:
    """Lookup by stable onbid/court key — survives DB rebuild (new numeric ids)."""
    lot = await get_lot_by_key(db, source, external_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lot not found")
    if enrich or fetch_detail:
        if enrich:
            await enrich_lot(db, settings, lot)
        else:
            from app.ingest.onbid_detail import enrich_lot_onbid_detail

            await enrich_lot_onbid_detail(db, settings, lot)
            await db.commit()
            await db.refresh(lot)
        lot = await get_lot_by_key(db, source, external_id)
        assert lot is not None
    return to_detail(lot)


@router.get("/lots/{lot_id}", response_model=LotDetail)
async def lot_detail(
    lot_id: int,
    enrich: bool = False,
    fetch_detail: bool = False,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LotDetail:
    lot = await get_lot(db, lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lot not found")
    if enrich or fetch_detail:
        if enrich:
            await enrich_lot(db, settings, lot)
        else:
            from app.ingest.onbid_detail import enrich_lot_onbid_detail

            await enrich_lot_onbid_detail(db, settings, lot)
            await db.commit()
            await db.refresh(lot)
        lot = await get_lot(db, lot_id)
        assert lot is not None
    return to_detail(lot)


@router.post("/ingest/onbid", response_model=IngestResponse)
async def ingest_onbid_endpoint(
    req: IngestRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    await seed_regions(db)
    if not settings.onbid_service_key:
        raise HTTPException(
            status_code=400,
            detail="ONBID_SERVICE_KEY is not configured. See docs/API_KEYS.md",
        )

    cleared = 0
    if req.clear_onbid:
        cleared = await _clear_onbid_lots(db)
    elif req.clear_demo:
        cleared = await _clear_demo_lots(db)

    run = await ingest_onbid(
        db,
        settings,
        max_pages=req.max_pages,
        page_size=req.page_size,
    )
    enriched = 0
    if req.enrich and run.lot_count > 0:
        lots = (
            await db.execute(
                select(AuctionLot)
                .where(AuctionLot.source == "onbid")
                .order_by(AuctionLot.id.desc())
                .limit(max(1, min(req.enrich_limit, 100)))
            )
        ).scalars().all()
        # Prefer Seoul/Gyeonggi/Incheon lots missing coords or market
        targets = [l for l in lots if l.region_code] or list(lots)
        enriched = await enrich_lots(db, settings, targets)

    status = run.status
    if run.lot_count == 0 and status == "ok":
        status = "empty"
    return IngestResponse(
        status=status,
        lot_count=run.lot_count,
        message=run.message,
        enriched=enriched,
        cleared_demo=cleared,
    )
