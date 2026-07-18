from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import get_db
from app.ingest.onbid import ingest_onbid
from app.models import AuctionLot, AuctionSchedule, NearbyTrade, PoiCache, Region
from app.schemas import (
    EnrichRequest,
    HealthOut,
    IngestRequest,
    IngestResponse,
    LotDetail,
    RegionOut,
    SearchRequest,
    SearchResponse,
)
from app.services.enrich import enrich_lot, enrich_lots
from app.services.lots import get_lot, search_lots, seed_regions, to_detail

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
    return HealthOut(
        status="ok",
        mode=mode,
        lot_count=total,
        onbid_lot_count=onbid_n,
        court_lot_count=court_n,
        demo_lot_count=demo_n,
        keys={
            "onbid": bool(settings.onbid_service_key),
            "molit": bool(settings.molit_service_key),
            "kakao": bool(settings.kakao_rest_key),
        },
    )


@router.post("/enrich", response_model=IngestResponse)
async def enrich_existing(
    req: EnrichRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> IngestResponse:
    """Re-enrich existing lots with Molit market (and Kakao POI if keyed)."""
    lots = (
        await db.execute(
            select(AuctionLot).order_by(AuctionLot.id.asc()).limit(max(1, min(req.limit, 100)))
        )
    ).scalars().all()
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
    return IngestResponse(
        status="ok",
        lot_count=len(lots),
        enriched=n,
        message=(
            f"enriched {n} lots "
            f"(market={req.fetch_market}, "
            f"pois={bool(settings.kakao_rest_key) and req.fetch_pois}, "
            f"detail={bool(settings.onbid_service_key) and req.fetch_detail})"
        ),
    )


@router.get("/regions", response_model=list[RegionOut])
async def list_regions(db: AsyncSession = Depends(get_db)) -> list[RegionOut]:
    await seed_regions(db)
    rows = (await db.execute(select(Region).order_by(Region.sido, Region.name))).scalars().all()
    return [RegionOut(code=r.code, name=r.name, sido=r.sido) for r in rows]


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest, db: AsyncSession = Depends(get_db)) -> SearchResponse:
    total, items = await search_lots(db, req)
    return SearchResponse(total=total, items=items)


@router.get("/lots/{lot_id}", response_model=LotDetail)
async def lot_detail(
    lot_id: int,
    enrich: bool = False,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> LotDetail:
    lot = await get_lot(db, lot_id)
    if lot is None:
        raise HTTPException(status_code=404, detail="Lot not found")
    if enrich:
        await enrich_lot(db, settings, lot)
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
