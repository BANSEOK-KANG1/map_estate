"""할인율·상권·마감·유찰 스크리닝 점수.

설계 목표
- 입찰 추천이 아님. 목록에서 상대 비교가 되게 분산을 확보한다.
- 시세·POI가 비어도 감정할인·마감·유찰만으로 차별화한다.
- 결측 항목은 중립(50)으로 채우지 않고 가중치를 재정규화한다.
  (구버전: 시세 결측=50 + infra=0 + 마감≥30일=10 + 감정≥40%할인=100 → 전부 44점)
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.models import PoiCache
from app.schemas import InsightScore


def discount_ratio(min_bid: int | None, base: int | None) -> float | None:
    """1 - min_bid/base. Positive = cheaper than base."""
    if min_bid is None or base is None or base <= 0:
        return None
    return round(1.0 - (min_bid / base), 4)


def discount_to_score(ratio: float | None) -> float | None:
    """Map discount ratio → 0..100. None = 결측(가중치에서 제외).

    구버전(40+150×r, 40%에서 포화)은 공매 전형 할인대에서 전부 100으로 뭉쳤다.
    0~80% 구간을 선형에 가깝게 펼친다.
    """
    if ratio is None:
        return None
    r = max(-0.2, min(1.0, float(ratio)))
    # 0%→18, 20%→38, 40%→58, 50%→68, 60%→78, 80%→98
    return round(max(5.0, min(98.0, 18.0 + r * 100.0)), 1)


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


def urgency_score(bid_end_at: datetime | None, now: datetime | None = None) -> float | None:
    """Closer deadline → higher urgency (5..100). None if unknown.

    구버전은 ≥30일이면 전부 10점이라 D-40~D-120이 구분되지 않았다.
    """
    if bid_end_at is None:
        return None
    now = now or datetime.utcnow()
    delta = bid_end_at - now
    if delta.total_seconds() <= 0:
        return 100.0
    days = delta.total_seconds() / 86400.0
    # half-life ≈ 18일: 0→100, 7→76, 14→58, 30→32, 60→10, 90→5
    raw = 100.0 * (0.5 ** (days / 18.0))
    return round(max(5.0, min(100.0, raw)), 1)


def fail_count_score(fail_count: int | None) -> float | None:
    """유찰 횟수 → 스크리닝 가산(가격 매력 신호). None만 제외, 0은 유효."""
    if fail_count is None:
        return None
    n = max(0, int(fail_count))
    # 0→22, 1→36, 2→48, 3→58, 5→74, 8→88, 12+→95
    return round(max(10.0, min(95.0, 22.0 + n * 12.0 - n * n * 0.35)), 1)


# 기본 가중치 (있는 항목만 재정규화)
_DEFAULT_WEIGHTS = {
    "appraisal": 0.32,
    "market": 0.28,
    "infra": 0.18,
    "urgency": 0.12,
    "fail": 0.10,
}


def combine_insight(
    discount_vs_appraisal: float | None,
    discount_vs_market: float | None,
    infra: float | None,
    urgency: float | None,
    *,
    fail_count: int | None = None,
    weight_appraisal: float = _DEFAULT_WEIGHTS["appraisal"],
    weight_market: float = _DEFAULT_WEIGHTS["market"],
    weight_infra: float = _DEFAULT_WEIGHTS["infra"],
    weight_urgency: float = _DEFAULT_WEIGHTS["urgency"],
    weight_fail: float = _DEFAULT_WEIGHTS["fail"],
) -> InsightScore:
    """결측 성분은 제외하고 가중치 재정규화. 전부 결측이면 total=None."""
    a = discount_to_score(discount_vs_appraisal)
    m = discount_to_score(discount_vs_market)
    f = fail_count_score(fail_count)
    # infra: None=미측정(제외), 0.0=측정했으나 POI 없음(반영)
    parts: list[tuple[float, float]] = []
    if a is not None:
        parts.append((a, weight_appraisal))
    if m is not None:
        parts.append((m, weight_market))
    if infra is not None:
        parts.append((float(infra), weight_infra))
    if urgency is not None:
        parts.append((float(urgency), weight_urgency))
    if f is not None:
        parts.append((f, weight_fail))

    if not parts:
        return InsightScore(
            discount_vs_appraisal=discount_vs_appraisal,
            discount_vs_market=discount_vs_market,
            infra=round(infra, 1) if infra is not None else None,
            urgency=round(urgency, 1) if urgency is not None else None,
            fail=round(f, 1) if f is not None else None,
            total=None,
        )

    tw = sum(w for _, w in parts)
    total = sum(s * w for s, w in parts) / tw
    return InsightScore(
        discount_vs_appraisal=discount_vs_appraisal,
        discount_vs_market=discount_vs_market,
        infra=round(infra, 1) if infra is not None else None,
        urgency=round(urgency, 1) if urgency is not None else None,
        fail=round(f, 1) if f is not None else None,
        total=round(total, 1),
    )


def score_from_fields(
    *,
    min_bid_manwon: int | None,
    appraisal_manwon: int | None,
    market_median_manwon: int | None,
    infra_score: float | None,
    bid_end_at: datetime | None,
    fail_count: int | None,
    now: datetime | None = None,
) -> InsightScore:
    """DB/API 필드만으로 점수 산출 (외부 API 불필요)."""
    return combine_insight(
        discount_ratio(min_bid_manwon, appraisal_manwon),
        discount_ratio(min_bid_manwon, market_median_manwon),
        infra_score,
        urgency_score(bid_end_at, now=now),
        fail_count=fail_count,
    )


def apply_lot_scores(lot: Any, *, now: datetime | None = None) -> InsightScore:
    """AuctionLot 필드에 할인비율·점수 기록."""
    insight = score_from_fields(
        min_bid_manwon=getattr(lot, "min_bid_manwon", None),
        appraisal_manwon=getattr(lot, "appraisal_manwon", None),
        market_median_manwon=getattr(lot, "market_median_manwon", None),
        infra_score=getattr(lot, "infra_score", None),
        bid_end_at=getattr(lot, "bid_end_at", None),
        fail_count=getattr(lot, "fail_count", None),
        now=now,
    )
    lot.discount_vs_appraisal = insight.discount_vs_appraisal
    lot.discount_vs_market = insight.discount_vs_market
    if insight.infra is not None:
        lot.infra_score = insight.infra
    lot.urgency_score = insight.urgency
    lot.total_score = insight.total
    return insight


def days_until(dt: datetime | None) -> int | None:
    if dt is None:
        return None
    return max(0, (dt - datetime.utcnow() + timedelta(hours=0)).days)
