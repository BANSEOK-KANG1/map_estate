"""원룸·오피스텔·빌라·다가구 검색·상세·추이."""

from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import Settings
from app.data.subway_stations import SEOUL_STATIONS
from app.ingest.molit_small_housing import HOUSING_LABELS
from app.models import Complex, IngestRun, Trade
from app.schemas import (
    AreaBucket,
    ComplexDetail,
    ComplexSummary,
    PoiSummary,
    ScoreBreakdown,
    SearchRequest,
    TradeOut,
    TrendPoint,
    TrendResponse,
)
from app.services import kakao, score

AREA_BUCKETS = [
    ("~20㎡", 0, 20.99),
    ("21~30㎡", 21, 30.99),
    ("31~40㎡", 31, 40.99),
    ("41~59㎡", 41, 59.99),
    ("60㎡+", 60, 9999),
]

POI_LABELS = {
    "subway": "지하철",
    "school": "학교",
    "hospital": "병원",
    "mart": "대형마트",
    "convenience": "편의점",
    "cafe": "카페",
    "food": "음식점",
}


def _median(values: list[float | int]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def _price_per_sqm(price: int, area: float) -> float:
    return price / area if area else 0.0


def _rent_score_price(deposit: int, monthly: int) -> int:
    return deposit + monthly * 100


def _trade_metric(t: Trade) -> int:
    if t.deal_kind == "rent":
        return _rent_score_price(t.price_manwon, t.monthly_rent_manwon or 0)
    return t.price_manwon


def _nearest_station(lat: float | None, lng: float | None) -> tuple[str | None, str | None, int | None]:
    if lat is None or lng is None:
        return None, None, None
    best = None
    best_m = 1e18
    for s in SEOUL_STATIONS:
        d = kakao.haversine_m(lat, lng, s["lat"], s["lng"])
        if d < best_m:
            best_m = d
            best = s
    if not best:
        return None, None, None
    walk = max(1, int(best_m / 80))
    return best["name"], best["line"], walk


def _build_tags(
    housing_type: str,
    build_year: int | None,
    walk_min: int | None,
    deal_kind: str | None,
    deposit: int | None,
    monthly: int | None,
    trend: float | None,
) -> list[str]:
    tags: list[str] = []
    if walk_min is not None:
        if walk_min <= 5:
            tags.append("역세권5분")
        elif walk_min <= 10:
            tags.append("도보10분")
    if build_year and build_year >= 2018:
        tags.append("신축급")
    elif build_year and build_year >= 2010:
        tags.append("준신축")
    labels = {"officetel": "오피스텔", "villa": "빌라원룸", "multi": "다가구"}
    tags.append(labels.get(housing_type, housing_type))
    if deal_kind == "rent":
        if deposit is not None and deposit <= 500:
            tags.append("저보증")
        if monthly is not None and monthly <= 50:
            tags.append("월세추천")
    if trend is not None and trend <= -3:
        tags.append("최근하락")
    elif trend is not None and trend >= 5:
        tags.append("상승세")
    return tags[:5]


async def _region_unit_prices(
    session: AsyncSession,
    region_code: str,
    deal_kind: str | None = None,
) -> list[float]:
    stmt = (
        select(Trade.price_manwon, Trade.exclusive_area, Trade.monthly_rent_manwon, Trade.deal_kind)
        .join(Complex)
        .where(Complex.region_code == region_code)
    )
    if deal_kind:
        stmt = stmt.where(Trade.deal_kind == deal_kind)
    result = await session.execute(stmt)
    out: list[float] = []
    for price, area, monthly, kind in result.all():
        if not area:
            continue
        if kind == "rent":
            out.append(_price_per_sqm(_rent_score_price(price, monthly or 0), area))
        else:
            out.append(_price_per_sqm(price, area))
    return out


def _percentile_rank(value: float, peers: list[float]) -> float:
    if not peers:
        return 50.0
    below = sum(1 for p in peers if p < value)
    return below / len(peers) * 100.0


async def summarize_complex(
    session: AsyncSession,
    complex_: Complex,
    region_name: str,
    region_unit_prices: list[float] | None = None,
    scores: ScoreBreakdown | None = None,
    trades: list[Trade] | None = None,
) -> ComplexSummary:
    if trades is None:
        trades = list(complex_.trades)
    if not trades:
        trades_result = await session.execute(
            select(Trade).where(Trade.complex_id == complex_.id).order_by(Trade.deal_date.desc())
        )
        trades = list(trades_result.scalars().all())

    prices = [t.price_manwon for t in trades]
    rents = [t.monthly_rent_manwon for t in trades if t.deal_kind == "rent"]
    areas = [t.exclusive_area for t in trades]
    floors = [t.floor for t in trades if t.floor is not None]
    unit_prices = [_price_per_sqm(_trade_metric(t), t.exclusive_area) for t in trades]
    latest = max(trades, key=lambda t: t.deal_date) if trades else None

    trend_pct = None
    if len(trades) >= 4:
        sorted_t = sorted(trades, key=lambda t: t.deal_date)
        half = len(sorted_t) // 2
        early = _median([_trade_metric(t) for t in sorted_t[:half]])
        late = _median([_trade_metric(t) for t in sorted_t[half:]])
        if early and late and early > 0:
            trend_pct = round((late - early) / early * 100.0, 1)

    if scores is None and region_unit_prices is not None and unit_prices:
        med_unit = _median(unit_prices) or 0
        pct = _percentile_rank(med_unit, region_unit_prices)
        scores = ScoreBreakdown(
            price=score.price_score_from_percentile(pct),
            infrastructure=0,
            commute=0,
            total=score.price_score_from_percentile(pct),
        )

    dominant_kind = None
    if trades:
        rent_n = sum(1 for t in trades if t.deal_kind == "rent")
        dominant_kind = "rent" if rent_n >= len(trades) / 2 else "sale"

    station, line, walk = _nearest_station(complex_.lat, complex_.lng)
    cutoff = date.today() - timedelta(days=180)
    recent_6m = sum(1 for t in trades if t.deal_date >= cutoff)

    tags = _build_tags(
        complex_.housing_type,
        complex_.build_year,
        walk,
        dominant_kind,
        int(_median(prices)) if prices else None,
        int(_median(rents)) if rents else None,
        trend_pct,
    )
    if complex_.facing:
        tags.insert(0, complex_.facing)
    if complex_.move_in_ok is True:
        tags.insert(0, "전입가능")
    elif complex_.move_in_ok is False:
        tags.insert(0, "전입문의")

    photos: list[str] = []
    try:
        photos = json.loads(complex_.photo_urls or "[]")
    except json.JSONDecodeError:
        photos = []

    avg_area = round(sum(areas) / len(areas), 1) if areas else None

    return ComplexSummary(
        id=complex_.id,
        name=complex_.name,
        housing_type=complex_.housing_type,
        housing_type_label=HOUSING_LABELS.get(complex_.housing_type, complex_.housing_type),
        region_code=complex_.region_code,
        region_name=region_name,
        dong=complex_.dong,
        jibun=complex_.jibun,
        road_name=complex_.road_name,
        build_year=complex_.build_year,
        lat=complex_.lat,
        lng=complex_.lng,
        trade_count=len(trades),
        deal_kind=dominant_kind,
        latest_price_manwon=latest.price_manwon if latest else None,
        latest_monthly_rent_manwon=(
            latest.monthly_rent_manwon if latest and latest.deal_kind == "rent" else None
        ),
        median_price_manwon=int(_median(prices)) if prices else None,
        median_monthly_rent_manwon=int(_median(rents)) if rents else None,
        median_pyeong_manwon=round((_median(unit_prices) or 0) * 3.3058, 1) if unit_prices else None,
        avg_exclusive_area=avg_area,
        avg_exclusive_pyeong=round(avg_area / 3.3058, 1) if avg_area else None,
        price_trend_pct=trend_pct,
        scores=scores,
        nearest_station=station,
        station_line=line,
        walk_minutes=walk,
        floor_min=min(floors) if floors else None,
        floor_max=max(floors) if floors else None,
        tags=tags[:6],
        recent_deal_count_6m=recent_6m,
        facing=complex_.facing or None,
        move_in_ok=complex_.move_in_ok,
        loan_manwon=complex_.loan_manwon,
        room_count=complex_.room_count,
        bath_count=complex_.bath_count,
        parking=complex_.parking,
        thumbnail_url=photos[0] if photos else None,
        latest_deal_date=latest.deal_date if latest else None,
        listed_at=complex_.listed_at,
    )


async def search_complexes(
    session: AsyncSession,
    settings: Settings,
    req: SearchRequest,
) -> tuple[list[ComplexSummary], int]:
    stmt = select(Complex).options(selectinload(Complex.trades), selectinload(Complex.region))
    if req.region_code:
        stmt = stmt.where(Complex.region_code == req.region_code)
    if req.housing_types:
        stmt = stmt.where(Complex.housing_type.in_(req.housing_types))
    if req.build_year_min is not None:
        stmt = stmt.where(Complex.build_year >= req.build_year_min)
    if req.query:
        q = f"%{req.query}%"
        stmt = stmt.where(or_(Complex.name.ilike(q), Complex.dong.ilike(q)))

    result = await session.execute(stmt)
    complexes = list(result.scalars().unique().all())

    filtered: list[tuple[Complex, list]] = []
    for c in complexes:
        trades = list(c.trades)
        if req.deal_kind:
            trades = [t for t in trades if t.deal_kind == req.deal_kind]
        if req.area_min is not None:
            trades = [t for t in trades if t.exclusive_area >= req.area_min]
        if req.area_max is not None:
            trades = [t for t in trades if t.exclusive_area <= req.area_max]
        if req.price_min is not None:
            trades = [t for t in trades if t.price_manwon >= req.price_min]
        if req.price_max is not None:
            trades = [t for t in trades if t.price_manwon <= req.price_max]
        if req.monthly_rent_min is not None:
            trades = [
                t
                for t in trades
                if t.deal_kind != "rent" or (t.monthly_rent_manwon or 0) >= req.monthly_rent_min
            ]
        if req.monthly_rent_max is not None:
            trades = [
                t
                for t in trades
                if t.deal_kind != "rent" or (t.monthly_rent_manwon or 0) <= req.monthly_rent_max
            ]
        if not trades:
            continue
        filtered.append((c, trades))

    region_prices_cache: dict[str, list[float]] = {}
    summaries: list[ComplexSummary] = []

    for c, trades in filtered:
        station, _line, walk = _nearest_station(c.lat, c.lng)
        if req.station_name and station != req.station_name:
            continue
        if req.max_walk_minutes is not None and (walk is None or walk > req.max_walk_minutes):
            continue

        region_name = c.region.name if c.region else c.region_code
        cache_key = f"{c.region_code}:{req.deal_kind or 'all'}"
        if cache_key not in region_prices_cache:
            region_prices_cache[cache_key] = await _region_unit_prices(
                session, c.region_code, req.deal_kind
            )
        peers = region_prices_cache[cache_key]

        unit_med = (
            _median([_price_per_sqm(_trade_metric(t), t.exclusive_area) for t in trades]) or 0
        )
        price_s = score.price_score_from_percentile(_percentile_rank(unit_med, peers))

        infra_s = 0.0
        if walk is not None:
            infra_s = max(0.0, min(100.0, (1 - walk / 20) * 70 + 30))
        commute_s = 0.0
        needs_place = (
            req.min_infra_score is not None
            or req.work_lat is not None
            or req.max_commute_minutes is not None
        )
        if needs_place and c.lat and c.lng:
            if settings.kakao_rest_key:
                await kakao.ensure_complex_coords(session, settings, c)
                pois = await kakao.get_or_fetch_pois(session, settings, c)
                infra_s = max(infra_s, score.infrastructure_score(pois))
            if req.work_lat is not None and req.work_lng is not None:
                minutes, _, _src = await kakao.driving_duration_minutes(
                    settings, c.lat, c.lng, req.work_lat, req.work_lng
                )
                commute_s = score.commute_score(
                    minutes, max_minutes=req.max_commute_minutes or 60.0
                )
                if req.max_commute_minutes is not None and minutes is not None:
                    if minutes > req.max_commute_minutes:
                        continue
        elif req.work_lat is not None and req.work_lng is not None and c.lat and c.lng:
            minutes, _, _ = await kakao.driving_duration_minutes(
                settings, c.lat, c.lng, req.work_lat, req.work_lng
            )
            commute_s = score.commute_score(minutes, max_minutes=req.max_commute_minutes or 60.0)

        if req.min_infra_score is not None and infra_s < req.min_infra_score:
            continue

        scores = score.combine_scores(
            price_s,
            infra_s,
            commute_s,
            req.weight_price,
            req.weight_infra,
            req.weight_commute,
        )
        summaries.append(
            await summarize_complex(
                session, c, region_name, peers, scores, trades=trades
            )
        )

    def sort_key(s: ComplexSummary):
        if req.sort_by == "price_asc":
            return (s.median_price_manwon or 10**9, s.median_monthly_rent_manwon or 10**9)
        if req.sort_by == "price_desc":
            return (-(s.median_price_manwon or 0), -(s.median_monthly_rent_manwon or 0))
        if req.sort_by == "area_desc":
            return -(s.avg_exclusive_area or 0)
        if req.sort_by == "recent":
            return -s.recent_deal_count_6m
        if req.sort_by == "walk":
            return s.walk_minutes if s.walk_minutes is not None else 999
        return -(s.scores.total if s.scores else 0)

    summaries.sort(key=sort_key)
    total = len(summaries)
    return summaries[req.offset : req.offset + req.limit], total


async def get_complex_detail(
    session: AsyncSession,
    settings: Settings,
    complex_id: int,
    work_lat: float | None = None,
    work_lng: float | None = None,
    weight_price: float = 0.35,
    weight_infra: float = 0.25,
    weight_commute: float = 0.4,
) -> ComplexDetail | None:
    result = await session.execute(
        select(Complex)
        .options(selectinload(Complex.trades), selectinload(Complex.region))
        .where(Complex.id == complex_id)
    )
    complex_ = result.scalar_one_or_none()
    if not complex_:
        return None

    region_name = complex_.region.name if complex_.region else complex_.region_code
    peers = await _region_unit_prices(session, complex_.region_code)
    unit_med = (
        _median([_price_per_sqm(_trade_metric(t), t.exclusive_area) for t in complex_.trades]) or 0
    )
    price_s = score.price_score_from_percentile(_percentile_rank(unit_med, peers))

    station, _, walk = _nearest_station(complex_.lat, complex_.lng)
    infra_s = max(0.0, min(100.0, (1 - (walk or 15) / 20) * 70 + 30)) if walk else 40.0
    commute_out = None
    commute_s = 0.0

    if settings.kakao_rest_key:
        await kakao.ensure_complex_coords(session, settings, complex_)
    pois = []
    if complex_.lat and complex_.lng and settings.kakao_rest_key:
        pois = await kakao.get_or_fetch_pois(session, settings, complex_)
        infra_s = max(infra_s, score.infrastructure_score(pois))
    if complex_.lat and complex_.lng and work_lat is not None and work_lng is not None:
        minutes, meters, src = await kakao.driving_duration_minutes(
            settings, complex_.lat, complex_.lng, work_lat, work_lng
        )
        commute_out = score.build_commute_out(minutes, meters, src)
        commute_s = commute_out.score

    scores = score.combine_scores(
        price_s, infra_s, commute_s, weight_price, weight_infra, weight_commute
    )
    summary = await summarize_complex(session, complex_, region_name, peers, scores)

    recent = sorted(complex_.trades, key=lambda t: t.deal_date, reverse=True)[:30]
    recent_trades = [
        TradeOut(
            deal_date=t.deal_date,
            deal_kind=t.deal_kind,
            exclusive_area=t.exclusive_area,
            price_manwon=t.price_manwon,
            monthly_rent_manwon=t.monthly_rent_manwon or 0,
            floor=t.floor,
            price_per_sqm_manwon=round(_price_per_sqm(_trade_metric(t), t.exclusive_area), 1),
        )
        for t in recent
    ]

    buckets = []
    for label, lo, hi in AREA_BUCKETS:
        bt = [t for t in complex_.trades if lo <= t.exclusive_area <= hi]
        buckets.append(
            AreaBucket(
                label=label,
                min_area=lo,
                max_area=hi,
                trade_count=len(bt),
                median_price_manwon=int(_median([t.price_manwon for t in bt]) or 0) or None,
            )
        )

    poi_summary = [
        PoiSummary(
            category=p.category,
            label=POI_LABELS.get(p.category, p.category),
            count=p.count,
            nearest_distance_m=p.nearest_distance_m,
        )
        for p in pois
    ]
    if not poi_summary and station:
        poi_summary = [
            PoiSummary(
                category="subway",
                label=f"지하철({station})",
                count=1,
                nearest_distance_m=(walk or 0) * 80.0,
            )
        ]

    photos: list[str] = []
    try:
        photos = json.loads(complex_.photo_urls or "[]")
    except json.JSONDecodeError:
        photos = []

    coverage = await trade_coverage(session)
    if coverage["data_source"] == "molit":
        data_note = (
            f"국토부 실거래 기준 (이 건물 최근거래 "
            f"{summary.latest_deal_date}). "
            "가격·면적·층은 신고 실거래입니다. "
            "향·전입·융자·사진·연락처는 데모 호가정보일 수 있습니다."
        )
    else:
        data_note = (
            f"데모 시드 데이터입니다 (최근거래 {summary.latest_deal_date}). "
            "국토부 API 원본이 아닙니다. "
            "MOLIT_SERVICE_KEY + /api/ingest 로 진짜 실거래를 넣으세요. "
            "향·전입·융자·사진·연락처도 데모입니다."
        )

    return ComplexDetail(
        **summary.model_dump(),
        recent_trades=recent_trades,
        area_buckets=buckets,
        poi_summary=poi_summary,
        commute=commute_out,
        photo_urls=photos,
        description=complex_.description or "",
        agent_name=complex_.agent_name or "",
        agent_phone=complex_.agent_phone or "",
        agent_office=complex_.agent_office or "",
        data_note=data_note,
    )


async def get_trends(
    session: AsyncSession,
    complex_id: int,
    area_min: float | None = None,
    area_max: float | None = None,
    deal_kind: str | None = None,
) -> TrendResponse | None:
    exists = await session.get(Complex, complex_id)
    if not exists:
        return None
    stmt = select(Trade).where(Trade.complex_id == complex_id)
    if area_min is not None:
        stmt = stmt.where(Trade.exclusive_area >= area_min)
    if area_max is not None:
        stmt = stmt.where(Trade.exclusive_area <= area_max)
    if deal_kind:
        stmt = stmt.where(Trade.deal_kind == deal_kind)
    result = await session.execute(stmt.order_by(Trade.deal_date))
    trades = list(result.scalars().all())

    grouped: dict[str, list[Trade]] = defaultdict(list)
    for t in trades:
        grouped[f"{t.deal_year:04d}-{t.deal_month:02d}"].append(t)

    points: list[TrendPoint] = []
    for ym in sorted(grouped.keys()):
        ts = grouped[ym]
        metrics = [_trade_metric(t) for t in ts]
        units = [_price_per_sqm(_trade_metric(t), t.exclusive_area) for t in ts]
        points.append(
            TrendPoint(
                year_month=ym,
                median_price_manwon=round(_median(metrics) or 0, 1),
                median_per_sqm_manwon=round(_median(units) or 0, 1),
                trade_count=len(ts),
            )
        )
    return TrendResponse(
        complex_id=complex_id,
        area_min=area_min,
        area_max=area_max,
        points=points,
    )


async def trade_coverage(session: AsyncSession) -> dict:
    """DB에 들어있는 실거래(또는 시드)의 실제 기간·출처."""
    max_d = await session.scalar(select(func.max(Trade.deal_date)))
    min_d = await session.scalar(select(func.min(Trade.deal_date)))
    ingest_ok = (
        await session.scalar(
            select(func.count()).select_from(IngestRun).where(IngestRun.status == "ok")
        )
        or 0
    )
    source = "molit" if ingest_ok > 0 else "demo"
    data_as_of = max_d.strftime("%Y-%m") if max_d else None
    return {
        "data_as_of": data_as_of,
        "trade_from": min_d.isoformat() if min_d else None,
        "trade_to": max_d.isoformat() if max_d else None,
        "data_source": source,
    }


async def health_stats(session: AsyncSession, settings: Settings) -> dict:
    trade_count = await session.scalar(select(func.count()).select_from(Trade)) or 0
    complex_count = await session.scalar(select(func.count()).select_from(Complex)) or 0
    coverage = await trade_coverage(session)
    return {
        "status": "ok",
        "molit_configured": bool(settings.molit_service_key),
        "kakao_configured": bool(settings.kakao_rest_key),
        "trade_count": trade_count,
        "complex_count": complex_count,
        **coverage,
    }
