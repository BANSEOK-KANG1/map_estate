"""Phase 4 loan plan / RuleConfig helpers."""

from app.analysis.loan_plan import (
    build_loan_scenarios,
    build_what_if_bundle,
    cash_ladder,
    estimate_acquisition_tax_won,
    estimate_holding_interest_won,
    pick_ltv_rates,
    rule_ref_from_model,
)
from app.analysis.calculator import compute_total_cost
from app.analysis.rules import usage_bucket


def test_usage_bucket():
    assert usage_bucket("아파트") == "주택"
    assert usage_bucket("근린생활시설") == "상가"


def test_tax_and_interest():
    assert estimate_acquisition_tax_won(tax_base_won=100_000_000, rate=0.011) == 1_100_000
    assert estimate_holding_interest_won(
        max_loan_won=100_000_000, annual_rate=0.05, hold_months=6
    ) == 2_500_000


def test_loan_scenarios_ranges():
    ref = rule_ref_from_model(
        type(
            "R",
            (),
            {
                "id": 1,
                "rule_key": "ltv_cap_housing",
                "source_label": "FSC",
                "source_url": "https://example",
                "effective_from": "2024-01-01",
                "notes": "",
                "value_json": '{"conservative":0.4,"base":0.5,"optimistic":0.6}',
            },
        )(),
        rule_key="ltv_cap_housing",
    )
    rows = build_loan_scenarios(
        collateral_won=400_000_000,
        total_cost_won=350_000_000,
        ltv_rates=pick_ltv_rates(ref.value if ref else {}),
        ltv_rule=ref,
        dsr_rule=None,
        interest_rule=None,
    )
    assert len(rows) == 3
    assert rows[0]["label"] == "conservative"
    assert rows[0]["max_loan_won"] == 160_000_000
    assert rows[0]["cash_needed_won"] == 190_000_000
    ladder = cash_ladder(rows, 350_000_000)
    assert ladder["cash_needed_min_won"] < ladder["cash_needed_max_won"]


def test_what_if_bundle_keys():
    cost = compute_total_cost(
        bid_won=300_000_000,
        assume_deposit_won=40_000_000,
        acquisition_tax_won=3_000_000,
        repair_won=10_000_000,
    )
    bundle = build_what_if_bundle(
        cost, conservative_exit_won=400_000_000, target_margin_ratio=0.15
    )
    assert set(bundle) >= {
        "deposit_half",
        "deposit_full",
        "eviction_delay",
        "loan_cut_20pct",
        "exit_drop_10pct",
    }
