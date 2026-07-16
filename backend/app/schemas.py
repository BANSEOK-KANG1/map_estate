from datetime import date

from pydantic import BaseModel, Field


class RegionOut(BaseModel):
    code: str
    name: str
    sido: str


class ScoreBreakdown(BaseModel):
    price: float = 0
    infrastructure: float = 0
    commute: float = 0
    total: float = 0


class ComplexSummary(BaseModel):
    id: int
    name: str
    housing_type: str
    housing_type_label: str
    region_code: str
    region_name: str
    dong: str
    jibun: str
    road_name: str
    build_year: int | None
    lat: float | None
    lng: float | None
    trade_count: int
    deal_kind: str | None = None
    latest_price_manwon: int | None
    latest_monthly_rent_manwon: int | None = None
    median_price_manwon: int | None
    median_monthly_rent_manwon: int | None = None
    median_pyeong_manwon: float | None
    avg_exclusive_area: float | None
    avg_exclusive_pyeong: float | None = None
    price_trend_pct: float | None = None
    scores: ScoreBreakdown | None = None
    nearest_station: str | None = None
    station_line: str | None = None
    walk_minutes: int | None = None
    floor_min: int | None = None
    floor_max: int | None = None
    tags: list[str] = Field(default_factory=list)
    recent_deal_count_6m: int = 0
    facing: str | None = None
    move_in_ok: bool | None = None
    loan_manwon: int | None = None
    room_count: int | None = None
    bath_count: int | None = None
    parking: bool | None = None
    thumbnail_url: str | None = None
    latest_deal_date: date | None = None
    listed_at: date | None = None


class ComplexDetail(ComplexSummary):
    recent_trades: list["TradeOut"] = Field(default_factory=list)
    area_buckets: list["AreaBucket"] = Field(default_factory=list)
    poi_summary: list["PoiSummary"] = Field(default_factory=list)
    commute: "CommuteOut | None" = None
    photo_urls: list[str] = Field(default_factory=list)
    description: str = ""
    agent_name: str = ""
    agent_phone: str = ""
    agent_office: str = ""
    data_note: str = (
        "실거래는 신고 기준이며 보통 1~2개월 지연됩니다. "
        "향·전입·융자·사진·연락처는 데모(호가형) 정보입니다."
    )


class TradeOut(BaseModel):
    deal_date: date
    deal_kind: str
    exclusive_area: float
    price_manwon: int
    monthly_rent_manwon: int = 0
    floor: int | None
    price_per_sqm_manwon: float


class AreaBucket(BaseModel):
    label: str
    min_area: float
    max_area: float
    trade_count: int
    median_price_manwon: int | None


class TrendPoint(BaseModel):
    year_month: str
    median_price_manwon: float
    median_per_sqm_manwon: float
    trade_count: int


class TrendResponse(BaseModel):
    complex_id: int
    area_min: float | None = None
    area_max: float | None = None
    points: list[TrendPoint]


class PoiSummary(BaseModel):
    category: str
    label: str
    count: int
    nearest_distance_m: float | None


class CommuteOut(BaseModel):
    mode: str
    duration_minutes: float | None
    distance_meters: float | None
    score: float
    source: str


class SearchRequest(BaseModel):
    region_code: str | None = None
    query: str | None = None
    housing_types: list[str] | None = None
    deal_kind: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    monthly_rent_min: int | None = None
    monthly_rent_max: int | None = None
    area_min: float | None = None
    area_max: float | None = None
    build_year_min: int | None = None
    station_name: str | None = None
    max_walk_minutes: int | None = None
    max_commute_minutes: float | None = None
    min_infra_score: float | None = None
    work_lat: float | None = None
    work_lng: float | None = None
    weight_price: float = 0.35
    weight_infra: float = 0.25
    weight_commute: float = 0.4
    sort_by: str = "score"
    limit: int = 80
    offset: int = 0


class SearchResponse(BaseModel):
    total: int
    items: list[ComplexSummary]
    data_as_of: str | None = None
    trade_from: str | None = None
    trade_to: str | None = None
    data_source: str = "demo"  # molit | demo
    listed_as_of: str | None = None
    note: str = (
        "가격·면적·층·거래일은 실거래(신고) 기준입니다. "
        "향·전입·융자·사진·연락처는 데모 호가정보일 수 있습니다. "
        "실거래 공개는 보통 1~2개월 지연됩니다."
    )


class IngestRequest(BaseModel):
    region_codes: list[str] | None = None
    months: int = 12
    force: bool = False
    sources: list[str] | None = None


class IngestStatus(BaseModel):
    started: bool
    message: str
    regions: int
    months: int


class HealthOut(BaseModel):
    status: str
    molit_configured: bool
    kakao_configured: bool
    trade_count: int
    complex_count: int
    data_as_of: str | None = None
    trade_from: str | None = None
    trade_to: str | None = None
    data_source: str = "demo"
