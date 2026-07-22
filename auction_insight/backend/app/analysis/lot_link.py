"""Hydrate analysis AuctionItem from screening AuctionLot (Phase 5)."""

from __future__ import annotations

import json
from typing import Any

from app.analysis.schemas import AuctionItemCreate


def manwon_to_won(manwon: int | float | None) -> int | None:
    if manwon is None:
        return None
    return int(round(float(manwon) * 10_000))


def lot_to_create_body(lot: Any) -> AuctionItemCreate:
    """Map AuctionLot columns → AuctionItemCreate (won units)."""
    source = getattr(lot, "source", "") or "onbid"
    if source not in ("court", "onbid"):
        source = "onbid"
    appraisal = manwon_to_won(getattr(lot, "appraisal_manwon", None))
    min_bid = manwon_to_won(getattr(lot, "min_bid_manwon", None))
    notes_parts = [
        f"AuctionLot#{getattr(lot, 'id', '')}에서 가져옴.",
        "공식 스크리닝 데이터 기준이며, 권리·점유 확정은 문서 근거가 필요합니다.",
    ]
    risk = _risk_flags_from_detail(getattr(lot, "detail_json", "") or "")
    if risk:
        notes_parts.append("위험칩: " + ", ".join(risk[:5]))
    return AuctionItemCreate(
        source=source,
        title=getattr(lot, "title", "") or getattr(lot, "address", "") or "",
        address=getattr(lot, "address", "") or "",
        usage=getattr(lot, "usage", "") or "",
        case_no=getattr(lot, "case_no", "") or "",
        court_or_org=getattr(lot, "court_name", "") or "",
        external_id=getattr(lot, "external_id", "") or "",
        lot_id=getattr(lot, "id", None),
        appraisal_won=appraisal,
        min_bid_won=min_bid,
        planned_price_won=min_bid if source == "onbid" else None,
        fail_count=int(getattr(lot, "fail_count", 0) or 0),
        lat=getattr(lot, "lat", None),
        lng=getattr(lot, "lng", None),
        source_url=getattr(lot, "source_url", "") or "",
        notes="\n".join(notes_parts),
    )


def linked_lot_dict(lot: Any) -> dict:
    """Compact snapshot for analysis UI (market / POI / scores)."""
    market_note = (getattr(lot, "market_note", "") or "").strip()
    sample = int(getattr(lot, "market_sample_count", 0) or 0)
    if not market_note:
        market_note = (
            f"인근 실거래 표본 {sample}건"
            if sample
            else "시세 표본 없음 — enrich 후 다시 확인"
        )
    return {
        "lot_id": getattr(lot, "id", None),
        "source": getattr(lot, "source", ""),
        "external_id": getattr(lot, "external_id", ""),
        "title": getattr(lot, "title", ""),
        "address": getattr(lot, "address", ""),
        "usage": getattr(lot, "usage", ""),
        "case_no": getattr(lot, "case_no", ""),
        "fail_count": int(getattr(lot, "fail_count", 0) or 0),
        "source_url": getattr(lot, "source_url", "") or "",
        "appraisal_manwon": getattr(lot, "appraisal_manwon", None),
        "min_bid_manwon": getattr(lot, "min_bid_manwon", None),
        "market": {
            "median_manwon": getattr(lot, "market_median_manwon", None),
            "pyeong_manwon": getattr(lot, "market_pyeong_manwon", None),
            "sample_count": sample,
            "note": market_note,
            "discount_vs_appraisal": getattr(lot, "discount_vs_appraisal", None),
            "discount_vs_market": getattr(lot, "discount_vs_market", None),
        },
        "infra": {
            "nearest_station": getattr(lot, "nearest_station", "") or "",
            "station_walk_minutes": getattr(lot, "station_walk_minutes", None),
            "infra_score": getattr(lot, "infra_score", None),
            "total_score": getattr(lot, "total_score", None),
        },
        "risk_flags": _risk_flags_from_detail(getattr(lot, "detail_json", "") or ""),
        "disclaimer": (
            "스크리닝 AuctionLot 스냅샷입니다. 입찰 직전 원문·등기·시세를 재확인하세요."
        ),
    }


def occupancy_stubs_from_lot(lot: Any) -> list[dict]:
    """HOLD stubs from Onbid detail_json — never confirmed without docs."""
    data = _parse_detail(getattr(lot, "detail_json", "") or "")
    if not data:
        return []
    stubs: list[dict] = []
    lease_count = int(data.get("lease_count") or 0)
    occupy_count = int(data.get("occupy_count") or 0)
    rows = data.get("lease_rows") or data.get("leases") or []
    if isinstance(rows, list) and rows:
        for i, row in enumerate(rows[:5]):
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or row.get("subtitle") or f"임차 {i+1}")
            stubs.append(
                {
                    "claim_kind": "housing",
                    "occupant_label": title[:120],
                    "notes": (
                        "온비드 임대차 목록에서 가져옴(HOLD). "
                        "전입·확정일자·보증금은 문서 근거로 입력하세요."
                    ),
                }
            )
    elif lease_count > 0:
        stubs.append(
            {
                "claim_kind": "housing",
                "occupant_label": f"온비드 임대차 {lease_count}건",
                "notes": "목록 건수만 있음 — 상세 행·문서로 확인 (HOLD)",
            }
        )
    if occupy_count > 0 and not stubs:
        stubs.append(
            {
                "claim_kind": "housing",
                "occupant_label": f"점유 관련 {occupy_count}건",
                "notes": "온비드 점유 목록 힌트(HOLD). 대항력 확정 금지.",
            }
        )
    return stubs


def _parse_detail(raw: str) -> dict:
    raw = (raw or "").strip()
    if not raw or raw == "{}":
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _risk_flags_from_detail(raw: str) -> list[str]:
    data = _parse_detail(raw)
    flags = []
    for f in data.get("risk_flags") or []:
        flags.append(str(f))
        if len(flags) >= 8:
            break
    return flags
