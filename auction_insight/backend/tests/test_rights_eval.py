"""Phase 3 rights / occupancy evaluation tests."""

from datetime import date
from types import SimpleNamespace

from app.analysis.rights_eval import (
    apply_evaluation,
    evaluate_court_right,
    evaluate_occupancy,
    evaluate_onbid_right,
    pick_malso_baseline,
)


def test_court_malso_extinguish_vs_assume():
    malso = date(2020, 1, 15)
    st, _ = evaluate_court_right(
        SimpleNamespace(event_date=date(2021, 5, 1)),
        malso_date=malso,
        is_baseline=False,
        docs_ok=True,
        has_evidence=True,
    )
    assert st == "EXTINGUISH"
    st2, _ = evaluate_court_right(
        SimpleNamespace(event_date=date(2019, 1, 1)),
        malso_date=malso,
        is_baseline=False,
        docs_ok=True,
        has_evidence=True,
    )
    assert st2 == "ASSUME"


def test_court_blocks_without_docs():
    st, note = evaluate_court_right(
        SimpleNamespace(event_date=date(2021, 1, 1)),
        malso_date=date(2020, 1, 1),
        is_baseline=False,
        docs_ok=False,
        has_evidence=True,
    )
    assert st == "HOLD"
    assert "확정 금지" in note


def test_onbid_tax_no_malso_extinguish():
    st, note = evaluate_onbid_right(
        SimpleNamespace(kind="tax", event_date=date(2018, 3, 1)),
        docs_ok=True,
        has_evidence=True,
    )
    assert st == "INFO"
    assert "말소" in note or "별도" in note


def test_housing_occupancy_vs_malso():
    st, _ = evaluate_occupancy(
        SimpleNamespace(
            claim_kind="housing",
            move_in_date=date(2019, 1, 1),
            fixed_date=date(2019, 2, 1),
            evidence_doc_id=1,
        ),
        source="court",
        malso_date=date(2020, 1, 1),
        docs_ok=True,
    )
    assert st == "ASSUME"


def test_commercial_occupancy_needs_fields():
    st, note = evaluate_occupancy(
        SimpleNamespace(
            claim_kind="commercial",
            business_reg_date=None,
            tax_invoice_ok=None,
            evidence_doc_id=1,
        ),
        source="court",
        malso_date=date(2020, 1, 1),
        docs_ok=True,
    )
    assert st == "HOLD"
    assert "사업자등록" in note


def test_pick_baseline_and_timeline():
    r1 = SimpleNamespace(
        id=1,
        kind="mortgage",
        label="1순위 근저당",
        event_date=date(2018, 1, 1),
        is_malso_baseline=0,
        priority_hint=1,
        amount_won=100_000_000,
        status="UNKNOWN",
        evidence_doc_id=1,
        evidence_excerpt="갑구",
        rule_track="court_malso",
        notes="",
    )
    r2 = SimpleNamespace(
        id=2,
        kind="seize",
        label="가압류",
        event_date=date(2021, 1, 1),
        is_malso_baseline=0,
        priority_hint=2,
        amount_won=10_000_000,
        status="UNKNOWN",
        evidence_doc_id=1,
        evidence_excerpt="을구",
        rule_track="court_malso",
        notes="",
    )
    assert pick_malso_baseline([r1, r2]) is r1
    item = SimpleNamespace(source="court", rights=[r1, r2], occupancies=[])
    out = apply_evaluation(item, docs_ok=True, persist=True)
    assert out["malso_date"] == "2018-01-01"
    assert r1.status == "INFO"
    assert r2.status == "EXTINGUISH"
    assert len(out["timeline"]) == 2
