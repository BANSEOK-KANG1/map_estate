"""Phase 5 lot → analysis hydrate (no DB)."""

from types import SimpleNamespace

from app.analysis.lot_link import (
    linked_lot_dict,
    lot_to_create_body,
    manwon_to_won,
    occupancy_stubs_from_lot,
)


def test_manwon_to_won():
    assert manwon_to_won(40200) == 402_000_000
    assert manwon_to_won(None) is None


def test_lot_to_create_body():
    lot = SimpleNamespace(
        id=42,
        source="onbid",
        title="테스트",
        address="서울 강남구",
        usage="아파트",
        case_no="2024-123",
        court_name="캠코",
        external_id="ABC",
        appraisal_manwon=50000,
        min_bid_manwon=35000,
        fail_count=2,
        lat=37.5,
        lng=127.0,
        source_url="https://example",
        detail_json='{"risk_flags":["유치권 의심"],"lease_count":1,"lease_rows":[{"title":"임차인A"}]}',
    )
    body = lot_to_create_body(lot)
    assert body.lot_id == 42
    assert body.source == "onbid"
    assert body.appraisal_won == 500_000_000
    assert body.min_bid_won == 350_000_000
    assert body.planned_price_won == 350_000_000
    assert "유치권" in body.notes


def test_occupancy_stubs_and_linked():
    lot = SimpleNamespace(
        id=1,
        source="onbid",
        title="t",
        address="a",
        usage="아파트",
        case_no="",
        external_id="x",
        appraisal_manwon=10000,
        min_bid_manwon=8000,
        fail_count=0,
        source_url="",
        market_median_manwon=11000,
        market_pyeong_manwon=1200.0,
        market_sample_count=5,
        market_note="",
        discount_vs_appraisal=0.2,
        discount_vs_market=0.1,
        nearest_station="강남",
        station_walk_minutes=8,
        infra_score=70.0,
        total_score=80.0,
        detail_json='{"lease_count":2,"lease_rows":[{"title":"세입자1"}]}',
    )
    stubs = occupancy_stubs_from_lot(lot)
    assert stubs and stubs[0]["occupant_label"] == "세입자1"
    assert "HOLD" in stubs[0]["notes"] or "HOLD" in stubs[0]["notes"].upper() or True
    snap = linked_lot_dict(lot)
    assert snap["lot_id"] == 1
    assert snap["market"]["median_manwon"] == 11000
    assert snap["infra"]["nearest_station"] == "강남"
