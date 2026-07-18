"""할인율·상권·마감 임박 점수."""

from __future__ import annotations

from datetime import datetime, timedelta

from app.models import PoiCache
from app.schemas import InsightScore


def discount_ratio(min_bid: int | None, base: int | None) -> float | None:
    """1 - min_bid/base. Positive = cheaper than base."""
    if min_bid is None or base is None or base <= 0:
        return None
    return round(1.0 - (min_bid / base), 4)


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


def urgency_score(bid_end_at: datetime | None, now: datetime | None = None) -> float:
    """Closer deadline → higher urgency (0..100)."""
    if bid_end_at is None:
        return 0.0
    now = now or datetime.utcnow()
    delta = bid_end_at - now
    if delta.total_seconds() <= 0:
        return 100.0
    days = delta.total_seconds() / 86400.0
    if days >= 30:
        return 10.0
    if days >= 14:
        return 40.0
    if days >= 7:
        return 65.0
    if days >= 3:
        return 85.0
    return 95.0


def discount_to_score(ratio: float | None) -> float:
    """Map discount ratio to 0..100 (higher discount = better deal score)."""
    if ratio is None:
        return 50.0
    # 0% discount → 40, 30% → 85, 50%+ → 100
    return round(max(0.0, min(100.0, 40.0 + ratio * 150.0)), 1)


def combine_insight(
    discount_vs_appraisal: float | None,
    discount_vs_market: float | None,
    infra: float,
    urgency: float,
    weight_appraisal: float = 0.25,
    weight_market: float = 0.35,
    weight_infra: float = 0.25,
    weight_urgency: float = 0.15,
) -> InsightScore:
    a = discount_to_score(discount_vs_appraisal)
    m = discount_to_score(discount_vs_market)
    total_w = weight_appraisal + weight_market + weight_infra + weight_urgency
    total = (
        weight_appraisal * a
        + weight_market * m
        + weight_infra * infra
        + weight_urgency * urgency
    ) / total_w
    return InsightScore(
        discount_vs_appraisal=discount_vs_appraisal,
        discount_vs_market=discount_vs_market,
        infra=round(infra, 1),
        urgency=round(urgency, 1),
        total=round(total, 1),
    )


def days_until(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return max(0, (dt - datetime.utcnow() + timedelta(hours=0)).days)
