from datetime import date, datetime

from pydantic import BaseModel, Field


class RegionOut(BaseModel):
    code: str
    name: str
    sido: str


class InsightScore(BaseModel):
    discount_vs_appraisal: float | None = None
    discount_vs_market: float | None = None
    infra: float | None = None
    urgency: float | None = None
    total: float | None = None


class MarketCompare(BaseModel):
    median_manwon: int | None = None
    pyeong_manwon: float | None = None
    sample_count: int = 0
    note: str = ""
    confidence: str = "low"  # low | medium | high


class ScheduleOut(BaseModel):
    round_no: int
    sale_date: date | None = None
    min_bid_manwon: int | None = None
    result: str = ""
    note: str = ""


class PoiOut(BaseModel):
    category: str
    category_label: str
    count: int
    nearest_distance_m: float | None = None
    places: list[dict] = Field(default_factory=list)


class LegalRiskOut(BaseModel):
    """온비드 물건상세 기반 권리·특약 요약 (확정 권리분석 아님)."""

    org_name: str = ""
    eviction_target: str = ""
    etc_note: str = ""
    utilization_note: str = ""
    location_note: str = ""
    risk_flags: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    lease_count: int = 0
    occupy_count: int = 0
    registry_count: int = 0
    appraisals: list[dict] = Field(default_factory=list)
    bid_rounds: list[dict] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    bid_info_status: str | None = None


class LotSummary(BaseModel):
    id: int
    source: str
    source_label: str
    external_id: str
    case_no: str
    court_name: str = ""
    title: str
    usage: str
    address: str
    region_code: str | None
    region_name: str | None
    dong: str
    exclusive_area: float | None
    build_year: int | None = None
    floor_info: str = ""
    appraisal_manwon: int | None
    min_bid_manwon: int | None
    fail_count: int
    status: str
    bid_end_at: datetime | None
    sale_date: date | None
    days_left: int | None = None
    lat: float | None
    lng: float | None
    source_url: str
    thumbnail_url: str | None = None
    nearest_station: str | None = None
    station_line: str | None = None
    station_walk_minutes: int | None = None
    scores: InsightScore | None = None
    market: MarketCompare | None = None
    highlights: list[str] = Field(default_factory=list)


class LotDetail(LotSummary):
    land_area: float | None = None
    description: str = ""
    photo_urls: list[str] = Field(default_factory=list)
    schedules: list[ScheduleOut] = Field(default_factory=list)
    pois: list[PoiOut] = Field(default_factory=list)
    legal: LegalRiskOut | None = None
    bid_start_at: datetime | None = None
    disclaimer: str = (
        "본 정보는 참고용입니다. 권리분석·입찰은 원문·현장·등기 확인이 필요합니다."
    )


class SearchRequest(BaseModel):
    sources: list[str] = Field(default_factory=lambda: ["onbid", "court"])
    region_codes: list[str] = Field(default_factory=list)
    min_price_manwon: int | None = None
    max_price_manwon: int | None = None
    min_fail_count: int | None = None
    max_fail_count: int | None = None
    status: str | None = "active"
    bid_end_before: datetime | None = None
    bid_end_after: datetime | None = None
    north: float | None = None
    south: float | None = None
    east: float | None = None
    west: float | None = None
    q: str | None = None
    limit: int = 100
    offset: int = 0


class SearchResponse(BaseModel):
    total: int
    items: list[LotSummary]


class IngestRequest(BaseModel):
    max_pages: int = 10
    page_size: int = 100
    enrich: bool = False
    clear_demo: bool = False
    clear_onbid: bool = False
    enrich_limit: int = 40


class IngestResponse(BaseModel):
    status: str
    lot_count: int
    message: str = ""
    enriched: int = 0
    cleared_demo: int = 0


class EnrichRequest(BaseModel):
    limit: int = 50
    fetch_market: bool = True
    fetch_pois: bool = True
    fetch_detail: bool = True


class HealthOut(BaseModel):
    status: str
    service: str = "auction_insight"
    mode: str = "demo"  # demo | real | mixed
    lot_count: int = 0
    onbid_lot_count: int = 0
    court_lot_count: int = 0
    demo_lot_count: int = 0
    keys: dict[str, bool] = Field(default_factory=dict)
    onbid_reachable: bool | None = None
