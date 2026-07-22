"""CRUD for RightEntry / OccupancyClaim + timeline evaluate."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.models import OccupancyClaim, RightEntry
from app.analysis.rights_eval import (
    OCC_KINDS,
    RIGHT_KINDS,
    apply_evaluation,
)
from app.analysis.service import get_item, recompute


def _parse_date(v: str | date | None) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


async def _docs_ok(session: AsyncSession, item_id: int) -> bool:
    item = await get_item(session, item_id)
    if item is None:
        return False
    # reuse serialize path: required docs missing → not ok
    from app.analysis.rules import get_rule
    import json

    docs_present = {d.doc_type for d in item.documents}
    req_key = "required_docs_court" if item.source == "court" else "required_docs_onbid"
    req_rule = await get_rule(session, req_key)
    required = []
    if req_rule:
        try:
            required = json.loads(req_rule.value_json).get("docs") or []
        except json.JSONDecodeError:
            required = []
    return all(d in docs_present for d in required)


async def create_right(session: AsyncSession, item_id: int, body: dict) -> RightEntry:
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    kind = body.get("kind") or "other"
    if kind not in RIGHT_KINDS:
        raise ValueError(f"invalid kind: {kind}")
    docs_ok = await _docs_ok(session, item_id)
    has_ev = bool(body.get("evidence_doc_id") and (body.get("evidence_excerpt") or "").strip())
    status = body.get("status") or ("HOLD" if not docs_ok or not has_ev else "HOLD")
    if status not in ("UNKNOWN", "HOLD", "INFO", "EXTINGUISH", "ASSUME"):
        raise ValueError("invalid status")
    if not docs_ok and status not in ("UNKNOWN", "HOLD", "INFO"):
        status = "HOLD"
    track = body.get("rule_track") or (
        "court_malso" if item.source == "court" else "onbid_tax_distribute"
    )
    if body.get("is_malso_baseline") and item.source == "court":
        for r in item.rights:
            r.is_malso_baseline = 0
    entry = RightEntry(
        item_id=item_id,
        kind=kind,
        label=body.get("label") or kind,
        amount_won=body.get("amount_won"),
        priority_hint=body.get("priority_hint"),
        event_date=_parse_date(body.get("event_date")),
        is_malso_baseline=1 if body.get("is_malso_baseline") else 0,
        status=status,
        evidence_doc_id=body.get("evidence_doc_id"),
        evidence_page=body.get("evidence_page"),
        evidence_excerpt=(body.get("evidence_excerpt") or "")[:2000],
        confirmed_at=datetime.utcnow() if body.get("confirm") else None,
        rule_track=track,
        notes=body.get("notes") or "",
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    await recompute(session, item_id)
    return entry


async def patch_right(session: AsyncSession, right_id: int, body: dict) -> RightEntry:
    entry = await session.get(RightEntry, right_id)
    if entry is None:
        raise LookupError("right not found")
    item = await get_item(session, entry.item_id)
    if item is None:
        raise LookupError("item not found")
    if "kind" in body and body["kind"] is not None:
        if body["kind"] not in RIGHT_KINDS:
            raise ValueError("invalid kind")
        entry.kind = body["kind"]
    for field in ("label", "amount_won", "priority_hint", "evidence_doc_id", "evidence_page", "notes"):
        if field in body and body[field] is not None:
            setattr(entry, field, body[field])
    if "evidence_excerpt" in body and body["evidence_excerpt"] is not None:
        entry.evidence_excerpt = str(body["evidence_excerpt"])[:2000]
    if "event_date" in body:
        entry.event_date = _parse_date(body["event_date"])
    if "rule_track" in body and body["rule_track"]:
        entry.rule_track = body["rule_track"]
    if body.get("is_malso_baseline"):
        for r in item.rights:
            if r.id != entry.id:
                r.is_malso_baseline = 0
        entry.is_malso_baseline = 1
    elif "is_malso_baseline" in body and body["is_malso_baseline"] is False:
        entry.is_malso_baseline = 0
    if "status" in body and body["status"]:
        docs_ok = await _docs_ok(session, entry.item_id)
        st = body["status"]
        if not docs_ok and st not in ("UNKNOWN", "HOLD", "INFO"):
            st = "HOLD"
        entry.status = st
    if body.get("confirm"):
        entry.confirmed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(entry)
    await recompute(session, entry.item_id)
    return entry


async def delete_right(session: AsyncSession, right_id: int) -> None:
    entry = await session.get(RightEntry, right_id)
    if entry is None:
        raise LookupError("right not found")
    item_id = entry.item_id
    await session.delete(entry)
    await session.commit()
    await recompute(session, item_id)


async def create_occupancy(session: AsyncSession, item_id: int, body: dict) -> OccupancyClaim:
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    kind = body.get("claim_kind") or "housing"
    if kind not in OCC_KINDS:
        raise ValueError("claim_kind must be housing|commercial")
    docs_ok = await _docs_ok(session, item_id)
    has_ev = bool(body.get("evidence_doc_id"))
    status = "HOLD" if not docs_ok or not has_ev else "HOLD"
    claim = OccupancyClaim(
        item_id=item_id,
        claim_kind=kind,
        occupant_label=body.get("occupant_label") or "",
        deposit_won=body.get("deposit_won"),
        monthly_rent_won=body.get("monthly_rent_won"),
        move_in_date=_parse_date(body.get("move_in_date")) if kind == "housing" else None,
        fixed_date=_parse_date(body.get("fixed_date")) if kind == "housing" else None,
        business_reg_date=_parse_date(body.get("business_reg_date"))
        if kind == "commercial"
        else None,
        tax_invoice_ok=body.get("tax_invoice_ok") if kind == "commercial" else None,
        status=status,
        evidence_doc_id=body.get("evidence_doc_id"),
        evidence_page=body.get("evidence_page"),
        evidence_excerpt=(body.get("evidence_excerpt") or "")[:2000],
        notes=body.get("notes") or "",
    )
    session.add(claim)
    await session.commit()
    await session.refresh(claim)
    await recompute(session, item_id)
    return claim


async def patch_occupancy(session: AsyncSession, occ_id: int, body: dict) -> OccupancyClaim:
    claim = await session.get(OccupancyClaim, occ_id)
    if claim is None:
        raise LookupError("occupancy not found")
    if "claim_kind" in body and body["claim_kind"]:
        if body["claim_kind"] not in OCC_KINDS:
            raise ValueError("invalid claim_kind")
        claim.claim_kind = body["claim_kind"]
    for field in (
        "occupant_label",
        "deposit_won",
        "monthly_rent_won",
        "tax_invoice_ok",
        "evidence_doc_id",
        "evidence_page",
        "notes",
        "status",
    ):
        if field in body and body[field] is not None:
            setattr(claim, field, body[field])
    for df in ("move_in_date", "fixed_date", "business_reg_date"):
        if df in body:
            setattr(claim, df, _parse_date(body[df]))
    if "evidence_excerpt" in body and body["evidence_excerpt"] is not None:
        claim.evidence_excerpt = str(body["evidence_excerpt"])[:2000]
    if body.get("confirm"):
        claim.confirmed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(claim)
    await recompute(session, claim.item_id)
    return claim


async def delete_occupancy(session: AsyncSession, occ_id: int) -> None:
    claim = await session.get(OccupancyClaim, occ_id)
    if claim is None:
        raise LookupError("occupancy not found")
    item_id = claim.item_id
    await session.delete(claim)
    await session.commit()
    await recompute(session, item_id)


async def evaluate_item(
    session: AsyncSession,
    item_id: int,
    *,
    apply_finance_suggest: bool = False,
) -> dict:
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    docs_ok = await _docs_ok(session, item_id)
    result = apply_evaluation(item, docs_ok=docs_ok, persist=True)
    if apply_finance_suggest and item.finance is not None:
        if result["suggested_assume_deposit_won"]:
            item.finance.assume_deposit_won = result["suggested_assume_deposit_won"]
        if result["suggested_assume_other_rights_won"]:
            item.finance.assume_other_rights_won = result[
                "suggested_assume_other_rights_won"
            ]
    await session.commit()
    await recompute(session, item_id)
    item = await get_item(session, item_id)
    from app.analysis.service import serialize_detail

    detail = serialize_detail(item)  # type: ignore[arg-type]
    detail["timeline_eval"] = result
    return detail


def serialize_right(r: RightEntry) -> dict:
    return {
        "id": r.id,
        "kind": r.kind,
        "label": r.label,
        "amount_won": r.amount_won,
        "priority_hint": r.priority_hint,
        "event_date": r.event_date.isoformat() if r.event_date else None,
        "is_malso_baseline": bool(r.is_malso_baseline),
        "status": r.status,
        "evidence_doc_id": r.evidence_doc_id,
        "evidence_page": r.evidence_page,
        "evidence_excerpt": r.evidence_excerpt,
        "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
        "rule_track": r.rule_track,
        "notes": r.notes,
    }


def serialize_occupancy(c: OccupancyClaim) -> dict:
    return {
        "id": c.id,
        "claim_kind": c.claim_kind,
        "occupant_label": c.occupant_label,
        "deposit_won": c.deposit_won,
        "monthly_rent_won": c.monthly_rent_won,
        "move_in_date": c.move_in_date.isoformat() if c.move_in_date else None,
        "fixed_date": c.fixed_date.isoformat() if c.fixed_date else None,
        "business_reg_date": c.business_reg_date.isoformat() if c.business_reg_date else None,
        "tax_invoice_ok": c.tax_invoice_ok,
        "status": c.status,
        "evidence_doc_id": c.evidence_doc_id,
        "evidence_page": c.evidence_page,
        "evidence_excerpt": c.evidence_excerpt,
        "confirmed_at": c.confirmed_at.isoformat() if c.confirmed_at else None,
        "notes": c.notes,
    }
