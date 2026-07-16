from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db import SessionLocal, get_db
from app.ingest.molit_small_housing import ingest_all, seed_regions
from app.schemas import (
    ComplexDetail,
    HealthOut,
    IngestRequest,
    IngestStatus,
    RegionOut,
    SearchRequest,
    SearchResponse,
    TrendResponse,
)
from app.services import complexes as complex_svc
from app.data.seoul_regions import SEOUL_REGIONS
from app.ingest.molit_small_housing import DEFAULT_SOURCES

router = APIRouter()


@router.get("/health", response_model=HealthOut)
async def health(
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    stats = await complex_svc.health_stats(db, settings)
    return HealthOut(**stats)


@router.get("/regions", response_model=list[RegionOut])
async def list_regions(db: AsyncSession = Depends(get_db)):
    await seed_regions(db)
    return [RegionOut(**r) for r in SEOUL_REGIONS]


@router.get("/housing-types")
async def housing_types():
    return [
        {"code": "officetel", "label": "오피스텔(원룸)"},
        {"code": "villa", "label": "연립·다세대"},
        {"code": "multi", "label": "단독·다가구"},
    ]


@router.post("/search", response_model=SearchResponse)
async def search(
    req: SearchRequest,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    items, total = await complex_svc.search_complexes(db, settings, req)
    coverage = await complex_svc.trade_coverage(db)
    source = coverage["data_source"]
    if source == "molit":
        note = (
            f"국토부 실거래 공개 데이터 기준 "
            f"({coverage['trade_from']} ~ {coverage['trade_to']}). "
            "가격·면적·층·거래일은 신고된 실거래입니다. "
            "향·전입·융자·사진·연락처는 데모 호가정보일 수 있습니다. "
            "공개는 보통 1~2개월 지연됩니다."
        )
    else:
        note = (
            f"현재 DB는 데모 시드입니다. 가격·면적·층·거래일 형태는 실거래와 같지만 "
            f"국토부 API 원본이 아닙니다 (기간 {coverage['trade_from']} ~ {coverage['trade_to']}). "
            "backend/.env 에 MOLIT_SERVICE_KEY 를 넣고 POST /api/ingest 하면 "
            "진짜 실거래로 바뀝니다."
        )
    return SearchResponse(
        total=total,
        items=items,
        data_as_of=coverage["data_as_of"],
        trade_from=coverage["trade_from"],
        trade_to=coverage["trade_to"],
        data_source=source,
        listed_as_of=coverage["data_as_of"] if source == "demo" else None,
        note=note,
    )


@router.get("/complexes/{complex_id}", response_model=ComplexDetail)
async def complex_detail(
    complex_id: int,
    work_lat: float | None = None,
    work_lng: float | None = None,
    weight_price: float = Query(0.4, ge=0, le=1),
    weight_infra: float = Query(0.3, ge=0, le=1),
    weight_commute: float = Query(0.3, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    detail = await complex_svc.get_complex_detail(
        db,
        settings,
        complex_id,
        work_lat=work_lat,
        work_lng=work_lng,
        weight_price=weight_price,
        weight_infra=weight_infra,
        weight_commute=weight_commute,
    )
    if not detail:
        raise HTTPException(status_code=404, detail="Complex not found")
    return detail


@router.get("/complexes/{complex_id}/trends", response_model=TrendResponse)
async def complex_trends(
    complex_id: int,
    area_min: float | None = None,
    area_max: float | None = None,
    db: AsyncSession = Depends(get_db),
):
    trends = await complex_svc.get_trends(db, complex_id, area_min, area_max)
    if not trends:
        raise HTTPException(status_code=404, detail="Complex not found")
    return trends


async def _run_ingest(req: IngestRequest, settings: Settings) -> None:
    sources = None
    if req.sources:
        parsed: list[tuple[str, str]] = []
        for s in req.sources:
            parts = s.split(":")
            if len(parts) == 2:
                parsed.append((parts[0], parts[1]))
        sources = parsed or None
    async with SessionLocal() as session:
        await ingest_all(
            session,
            settings,
            region_codes=req.region_codes,
            months=req.months,
            force=req.force,
            sources=sources,
        )


@router.post("/ingest", response_model=IngestStatus)
async def trigger_ingest(
    req: IngestRequest,
    background: BackgroundTasks,
    settings: Settings = Depends(get_settings),
):
    if not settings.molit_service_key:
        raise HTTPException(
            status_code=400,
            detail="MOLIT_SERVICE_KEY is not set. Use POST /api/demo/seed for sample data.",
        )
    regions = len(req.region_codes) if req.region_codes else 25
    background.add_task(_run_ingest, req, settings)
    return IngestStatus(
        started=True,
        message=(
            "Ingest started (officetel/villa/multi · sale/rent). "
            f"sources={len(req.sources) if req.sources else len(DEFAULT_SOURCES)}"
        ),
        regions=regions,
        months=req.months,
    )
