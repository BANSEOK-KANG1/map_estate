"""Screening score algorithm tests."""

from datetime import datetime, timedelta

from app.services.score import (
    combine_insight,
    discount_to_score,
    fail_count_score,
    score_from_fields,
    urgency_score,
)


def test_discount_curve_spreads_typical_auction_range():
    """딥할인대(50/80/90%)도 서로 벌어져야 한다."""
    s50 = discount_to_score(0.50)
    s80 = discount_to_score(0.80)
    s90 = discount_to_score(0.90)
    assert s50 is not None and s80 is not None and s90 is not None
    assert s50 < s80 < s90
    assert s90 - s80 >= 10.0
    assert s80 < 90


def test_missing_market_no_longer_collapses_to_44():
    """구버전: 감정≥40% + 시세결측50 + infra0 + 마감≥30일10 → 전부 44."""
    now = datetime(2026, 7, 23)
    end = now + timedelta(days=97)
    a = discount_to_score(0.50)  # was 100
    assert a is not None and a < 100
    insight = combine_insight(
        0.50,
        None,  # market missing — excluded, not 50
        None,  # infra unknown — excluded, not 0
        urgency_score(end, now=now),
        fail_count=2,
    )
    assert insight.total is not None
    assert insight.total != 44.0
    assert 25.0 <= insight.total <= 85.0


def test_different_discounts_rank_differently():
    now = datetime(2026, 7, 23)
    end = now + timedelta(days=60)
    low = score_from_fields(
        min_bid_manwon=8000,
        appraisal_manwon=10000,  # 20%
        market_median_manwon=None,
        infra_score=None,
        bid_end_at=end,
        fail_count=0,
        now=now,
    )
    high = score_from_fields(
        min_bid_manwon=4000,
        appraisal_manwon=10000,  # 60%
        market_median_manwon=None,
        infra_score=None,
        bid_end_at=end,
        fail_count=3,
        now=now,
    )
    assert low.total is not None and high.total is not None
    assert high.total - low.total >= 8.0


def test_urgency_distinguishes_far_deadlines():
    now = datetime(2026, 7, 23)
    u40 = urgency_score(now + timedelta(days=40), now=now)
    u90 = urgency_score(now + timedelta(days=90), now=now)
    assert u40 is not None and u90 is not None
    assert u40 > u90
    assert u90 >= 2.0


def test_fail_count_score_monotonic():
    assert fail_count_score(0) < fail_count_score(2) < fail_count_score(5)
