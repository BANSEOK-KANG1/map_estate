"""Price / infrastructure / commute scoring."""

from __future__ import annotations

from app.models import PoiCache
from app.schemas import CommuteOut, ScoreBreakdown


def price_score_from_percentile(percentile: float) -> float:
    """Lower unit price vs peers → higher score. percentile 0..100 (0=cheapest)."""
    return max(0.0, min(100.0, 100.0 - percentile))


def infrastructure_score(pois: list[PoiCache]) -> float:
    if not pois:
        return 0.0
    weights = {
        "subway": 0.30,
        "school": 0.15,
        "hospital": 0.15,
        "mart": 0.15,
        "convenience": 0.10,
        "cafe": 0.08,
        "food": 0.07,
    }
    by_cat = {p.category: p for p in pois}
    score = 0.0
    for cat, w in weights.items():
        p = by_cat.get(cat)
        if not p:
            continue
        count_part = min(p.count / 5.0, 1.0) * 60.0
        dist_part = 0.0
        if p.nearest_distance_m is not None:
            dist_part = max(0.0, 1.0 - p.nearest_distance_m / 800.0) * 40.0
        score += w * (count_part + dist_part)
    return round(min(100.0, score), 1)


def commute_score(duration_minutes: float | None, max_minutes: float = 60.0) -> float:
    if duration_minutes is None:
        return 0.0
    if duration_minutes <= 0:
        return 100.0
    if duration_minutes >= max_minutes * 1.5:
        return 0.0
    return round(max(0.0, min(100.0, (1.0 - duration_minutes / max_minutes) * 100.0)), 1)


def combine_scores(
    price: float,
    infrastructure: float,
    commute: float,
    weight_price: float = 0.4,
    weight_infra: float = 0.3,
    weight_commute: float = 0.3,
) -> ScoreBreakdown:
    total_w = weight_price + weight_infra + weight_commute
    if total_w <= 0:
        total_w = 1.0
    wp, wi, wc = weight_price / total_w, weight_infra / total_w, weight_commute / total_w
    total = wp * price + wi * infrastructure + wc * commute
    return ScoreBreakdown(
        price=round(price, 1),
        infrastructure=round(infrastructure, 1),
        commute=round(commute, 1),
        total=round(total, 1),
    )


def build_commute_out(
    minutes: float | None,
    meters: float | None,
    source: str,
    max_minutes: float = 60.0,
) -> CommuteOut:
    return CommuteOut(
        mode="driving",
        duration_minutes=round(minutes, 1) if minutes is not None else None,
        distance_meters=round(meters, 1) if meters is not None else None,
        score=commute_score(minutes, max_minutes=max_minutes),
        source=source,
    )
