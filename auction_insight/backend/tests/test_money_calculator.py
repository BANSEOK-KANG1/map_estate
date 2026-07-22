"""Unit tests for money safety & calculator (no DB)."""

from app.analysis.calculator import compute_bid_ceiling, compute_total_cost
from app.analysis.money import detect_digit_errors, parse_user_amount, to_triple
from app.analysis.pii import mask_pii


def test_triple_units():
    t = to_triple(402_000_000)
    assert t is not None
    assert t.won == 402_000_000
    assert abs(t.manwon - 40200) < 1e-6
    assert abs(t.eok - 4.02) < 1e-6


def test_digit_error_10x():
    warnings = detect_digit_errors(
        appraisal_won=402_000_000,
        min_bid_won=40_200_000,
    )
    codes = {w["code"] for w in warnings}
    assert "DIGIT_FACTOR" in codes


def test_parse_manwon():
    assert parse_user_amount(raw=4020, unit="manwon") == 40_200_000


def test_total_cost_and_ceiling():
    cost = compute_total_cost(
        bid_won=300_000_000,
        assume_deposit_won=50_000_000,
        acquisition_tax_won=3_300_000,
        registry_legal_won=1_500_000,
        repair_won=10_000_000,
        eviction_won=3_000_000,
        contingency_won=5_000_000,
    )
    assert cost.total_cost_won == 300_000_000 + 50_000_000 + 3_300_000 + 1_500_000 + 10_000_000 + 3_000_000 + 5_000_000
    ceiling = compute_bid_ceiling(
        conservative_exit_won=400_000_000,
        target_margin_ratio=0.15,
        costs_excluding_bid_won=cost.costs_excluding_bid - 50_000_000,
        assume_amount_won=50_000_000,
        finance_cost_won=0,
    )
    # 400M - 60M margin - costs_ex - 50M assume
    assert ceiling["bid_ceiling_won"] < 400_000_000


def test_mask_pii():
    text, masked = mask_pii("주민 900101-1234567 연락 010-1234-5678")
    assert masked is True
    assert "1234567" not in text
    assert "1234" not in text or "****" in text
