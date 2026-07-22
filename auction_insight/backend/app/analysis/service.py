"""Analysis service: create items, recompute verdict/costs."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analysis.calculator import (
    compute_bid_ceiling,
    compute_total_cost,
)
from app.analysis.loan_plan import (
    build_loan_scenarios,
    build_what_if_bundle,
    cash_ladder,
    custom_what_if,
    estimate_acquisition_tax_won,
    pick_ltv_rates,
    rule_ref_from_model,
)
from app.analysis.models import (
    AnalysisRun,
    AuctionItem,
    FinanceProfile,
    LoanScenario,
)
from app.analysis.money import detect_digit_errors, parse_user_amount, triple_dict
from app.analysis.rights_eval import apply_evaluation
from app.analysis.rules import get_rule, seed_rules, usage_bucket
from app.analysis.schemas import AuctionItemCreate, FinanceUpdate


REQUIRED_DOC_LABELS = {
    "registry": "등기부등본",
    "appraisal": "감정평가서",
    "sale_spec": "매각물건명세서",
    "onbid_notice": "온비드 원문 공고·특약",
}


def _resolve_won(
    won: int | None,
    manwon: float | None,
) -> int | None:
    if won is not None:
        return won
    if manwon is not None:
        return parse_user_amount(raw=manwon, unit="manwon")
    return None


async def create_item(session: AsyncSession, body: AuctionItemCreate) -> AuctionItem:
    await seed_rules(session)
    if body.source not in ("court", "onbid"):
        raise ValueError("source must be court or onbid")
    appraisal = _resolve_won(body.appraisal_won, body.appraisal_manwon)
    min_bid = _resolve_won(body.min_bid_won, body.min_bid_manwon)
    planned = _resolve_won(body.planned_price_won, body.planned_price_manwon)
    item = AuctionItem(
        source=body.source,
        external_id=body.external_id,
        lot_id=body.lot_id,
        case_no=body.case_no,
        court_or_org=body.court_or_org,
        title=body.title or body.address,
        usage=body.usage,
        address=body.address,
        appraisal_won=appraisal,
        min_bid_won=min_bid,
        planned_price_won=planned,
        fail_count=body.fail_count,
        lat=body.lat,
        lng=body.lng,
        source_url=body.source_url,
        notes=body.notes,
        status="active",
    )
    session.add(item)
    await session.flush()
    fin = FinanceProfile(
        item_id=item.id,
        bid_won=min_bid or planned or appraisal,
        conservative_exit_won=appraisal,
        target_margin_ratio=0.15,
        # tax left 0 until RuleConfig applied explicitly — not silent hardcode
        acquisition_tax_won=0,
        registry_legal_won=1_500_000,
        repair_won=10_000_000,
        eviction_won=3_000_000,
        contingency_won=5_000_000,
    )
    session.add(fin)
    await session.commit()
    await session.refresh(item)
    await recompute(session, item.id)
    return await get_item(session, item.id)  # type: ignore[return-value]


async def get_item(session: AsyncSession, item_id: int) -> AuctionItem | None:
    return (
        await session.execute(
            select(AuctionItem)
            .options(
                selectinload(AuctionItem.finance),
                selectinload(AuctionItem.documents),
                selectinload(AuctionItem.rights),
                selectinload(AuctionItem.occupancies),
                selectinload(AuctionItem.loan_scenarios),
                selectinload(AuctionItem.analysis_runs),
            )
            .where(AuctionItem.id == item_id)
        )
    ).scalar_one_or_none()


async def list_items(
    session: AsyncSession,
    *,
    source: str | None = None,
    limit: int = 50,
) -> list[AuctionItem]:
    stmt = select(AuctionItem).options(selectinload(AuctionItem.analysis_runs))
    if source:
        stmt = stmt.where(AuctionItem.source == source)
    stmt = stmt.order_by(AuctionItem.id.desc()).limit(min(limit, 200))
    return list((await session.execute(stmt)).scalars().all())


async def update_finance(
    session: AsyncSession,
    item_id: int,
    body: FinanceUpdate,
) -> AuctionItem:
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    fin = item.finance
    if fin is None:
        fin = FinanceProfile(item_id=item.id)
        session.add(fin)
        await session.flush()
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(fin, k, v)
    await session.commit()
    return await recompute(session, item_id)


async def recompute(session: AsyncSession, item_id: int) -> AuctionItem:
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    fin = item.finance
    if fin is None:
        fin = FinanceProfile(item_id=item.id, bid_won=item.min_bid_won)
        session.add(fin)
        await session.flush()

    bid = fin.bid_won or item.min_bid_won or item.planned_price_won or 0
    cost = compute_total_cost(
        bid_won=bid,
        assume_deposit_won=fin.assume_deposit_won,
        assume_other_rights_won=fin.assume_other_rights_won,
        acquisition_tax_won=fin.acquisition_tax_won,
        vat_won=fin.vat_won,
        registry_legal_won=fin.registry_legal_won,
        unpaid_mgmt_won=fin.unpaid_mgmt_won,
        repair_won=fin.repair_won,
        eviction_won=fin.eviction_won,
        loan_interest_won=fin.loan_interest_won,
        disposal_cost_won=fin.disposal_cost_won,
        contingency_won=fin.contingency_won,
    )

    # Loan ranges from RuleConfig (not hardcoded in UI)
    bucket = usage_bucket(item.usage)
    region = item.region_code or "*"
    ltv_key = "ltv_cap_commercial" if bucket == "상가" else "ltv_cap_housing"
    dsr_key = "dsr_cap_housing"  # commercial DSR often N/A; still surface housing cap for apt-like
    ltv_rule_m = await get_rule(session, ltv_key, region_code=region, usage=bucket)
    dsr_rule_m = await get_rule(session, dsr_key, region_code=region, usage="주택")
    interest_rule_m = await get_rule(
        session, "loan_interest_rate_hint", region_code=region, usage="*"
    )
    ltv_ref = rule_ref_from_model(ltv_rule_m, rule_key=ltv_key)
    dsr_ref = rule_ref_from_model(dsr_rule_m, rule_key=dsr_key)
    interest_ref = rule_ref_from_model(interest_rule_m, rule_key="loan_interest_rate_hint")
    ltv_rates = pick_ltv_rates(ltv_ref.value if ltv_ref else {})

    hold_months = 6.0
    if interest_ref and interest_ref.value.get("hold_months_default"):
        try:
            hold_months = float(interest_ref.value["hold_months_default"])
        except (TypeError, ValueError):
            hold_months = 6.0

    # clear old scenarios
    for old in list(item.loan_scenarios):
        await session.delete(old)
    await session.flush()

    exit_won = fin.conservative_exit_won or item.appraisal_won or 0
    collateral = exit_won or item.appraisal_won or bid or 0
    planned = build_loan_scenarios(
        collateral_won=collateral,
        total_cost_won=cost.total_cost_won,
        ltv_rates=ltv_rates,
        ltv_rule=ltv_ref,
        dsr_rule=dsr_ref,
        interest_rule=interest_ref,
        hold_months=hold_months,
    )
    # Optionally sync base-scenario interest hint into finance if still 0
    base_row = next((r for r in planned if r["label"] == "base"), None)
    if base_row and fin.loan_interest_won == 0 and base_row.get("interest_hint_won"):
        fin.loan_interest_won = int(base_row["interest_hint_won"])
        # refresh cost with updated interest
        cost = compute_total_cost(
            bid_won=bid,
            assume_deposit_won=fin.assume_deposit_won,
            assume_other_rights_won=fin.assume_other_rights_won,
            acquisition_tax_won=fin.acquisition_tax_won,
            vat_won=fin.vat_won,
            registry_legal_won=fin.registry_legal_won,
            unpaid_mgmt_won=fin.unpaid_mgmt_won,
            repair_won=fin.repair_won,
            eviction_won=fin.eviction_won,
            loan_interest_won=fin.loan_interest_won,
            disposal_cost_won=fin.disposal_cost_won,
            contingency_won=fin.contingency_won,
        )
        planned = build_loan_scenarios(
            collateral_won=collateral,
            total_cost_won=cost.total_cost_won,
            ltv_rates=ltv_rates,
            ltv_rule=ltv_ref,
            dsr_rule=dsr_ref,
            interest_rule=interest_ref,
            hold_months=hold_months,
        )

    for row in planned:
        session.add(
            LoanScenario(
                item_id=item.id,
                label=row["label"],
                max_loan_won=row["max_loan_won"],
                cash_needed_won=row["cash_needed_won"],
                rule_ids_json=json.dumps(row.get("rule_ids") or []),
                notes=row.get("notes") or "",
                is_range_note=row.get("is_range_note")
                or "대출은 확정액이 아니라 가정 범위입니다.",
            )
        )

    docs_present = {d.doc_type for d in item.documents}
    req_key = "required_docs_court" if item.source == "court" else "required_docs_onbid"
    req_rule = await get_rule(session, req_key)
    required = []
    if req_rule:
        try:
            required = json.loads(req_rule.value_json).get("docs") or []
        except json.JSONDecodeError:
            required = []
    missing = [d for d in required if d not in docs_present]

    # Rights must not be confirmed without docs
    rights_note = (
        "필수 문서가 없어 권리관계를 확정하지 않습니다 (UNKNOWN/HOLD)."
        if missing
        else "문서가 일부 있습니다. 각 권리 항목은 원문 근거가 있을 때만 확정하세요."
    )
    for r in item.rights:
        if missing and r.status not in ("UNKNOWN", "HOLD", "INFO"):
            r.status = "HOLD"
            r.notes = (r.notes or "") + " [자동] 필수문서 부족으로 HOLD"

    digit_warn = detect_digit_errors(
        appraisal_won=item.appraisal_won,
        min_bid_won=item.min_bid_won,
        planned_price_won=item.planned_price_won,
    )

    finance_incomplete = (
        not fin.bid_won
        or fin.conservative_exit_won is None
        or fin.acquisition_tax_won == 0
    )
    beginner_ban = bool(missing) or finance_incomplete

    if beginner_ban and missing:
        verdict = "BEGINNER_BAN"
    elif beginner_ban:
        verdict = "HOLD"
    elif digit_warn or fin.assume_deposit_won > 0:
        verdict = "REVIEW_CONDITIONAL"
    else:
        verdict = "REVIEW_OK"

    assume = fin.assume_deposit_won + fin.assume_other_rights_won
    costs_ex = cost.costs_excluding_bid - assume
    ceiling = None
    if exit_won:
        ceiling = compute_bid_ceiling(
            conservative_exit_won=exit_won,
            target_margin_ratio=fin.target_margin_ratio,
            costs_excluding_bid_won=costs_ex,
            assume_amount_won=assume,
            finance_cost_won=fin.loan_interest_won,
        )

    check_next = []
    for m in missing:
        check_next.append(f"필수문서 추가: {REQUIRED_DOC_LABELS.get(m, m)}")
    if fin.acquisition_tax_won == 0:
        check_next.append(
            "취득세를 RuleConfig·세무사 기준으로 입력하세요 (현재 0 — UNKNOWN)."
        )
    if not item.rights:
        check_next.append("등기 갑·을구 권리를 문서 근거·등기일과 함께 입력하세요.")
    if not item.occupancies:
        check_next.append("점유·임차(주택/상가 분리)를 입력하고 대항력을 평가하세요.")
    for w in digit_warn:
        check_next.append(w["message"])

    summary = (
        f"판정={verdict}. 총투입액={cost.total_cost_won:,}원. "
        f"필수문서 결여={len(missing)}건."
    )
    run = AnalysisRun(
        item_id=item.id,
        verdict=verdict,
        missing_docs_json=json.dumps(missing, ensure_ascii=False),
        warnings_json=json.dumps(digit_warn, ensure_ascii=False),
        total_cost_won=cost.total_cost_won,
        bid_ceiling_won=(ceiling or {}).get("bid_ceiling_won"),
        summary=summary,
        created_at=datetime.utcnow(),
    )
    session.add(run)
    await session.commit()
    return (await get_item(session, item_id))  # type: ignore[return-value]


def serialize_detail(item: AuctionItem) -> dict:
    runs = sorted(item.analysis_runs, key=lambda r: r.id, reverse=True)
    latest = runs[0] if runs else None
    fin = item.finance
    bid = (fin.bid_won if fin else None) or item.min_bid_won or 0
    cost = compute_total_cost(
        bid_won=bid or 0,
        assume_deposit_won=fin.assume_deposit_won if fin else 0,
        assume_other_rights_won=fin.assume_other_rights_won if fin else 0,
        acquisition_tax_won=fin.acquisition_tax_won if fin else 0,
        vat_won=fin.vat_won if fin else 0,
        registry_legal_won=fin.registry_legal_won if fin else 0,
        unpaid_mgmt_won=fin.unpaid_mgmt_won if fin else 0,
        repair_won=fin.repair_won if fin else 0,
        eviction_won=fin.eviction_won if fin else 0,
        loan_interest_won=fin.loan_interest_won if fin else 0,
        disposal_cost_won=fin.disposal_cost_won if fin else 0,
        contingency_won=fin.contingency_won if fin else 0,
    )
    exit_won = (fin.conservative_exit_won if fin else None) or item.appraisal_won or 0
    assume = (fin.assume_deposit_won if fin else 0) + (
        fin.assume_other_rights_won if fin else 0
    )
    costs_ex = cost.costs_excluding_bid - assume
    ceiling = None
    if exit_won and fin:
        ceiling = compute_bid_ceiling(
            conservative_exit_won=exit_won,
            target_margin_ratio=fin.target_margin_ratio,
            costs_excluding_bid_won=costs_ex,
            assume_amount_won=assume,
            finance_cost_won=fin.loan_interest_won,
        )
    what_if = build_what_if_bundle(
        cost,
        conservative_exit_won=exit_won or 0,
        target_margin_ratio=fin.target_margin_ratio if fin else 0.15,
    )
    missing = json.loads(latest.missing_docs_json) if latest else []
    digit_warn = detect_digit_errors(
        appraisal_won=item.appraisal_won,
        min_bid_won=item.min_bid_won,
        planned_price_won=item.planned_price_won,
    )
    check_next = [REQUIRED_DOC_LABELS.get(m, m) for m in missing]
    if fin and fin.acquisition_tax_won == 0:
        check_next.append("취득세 미입력 — RuleConfig·전문가 확인")

    loan_rows = [
        {
            "label": s.label,
            "max_loan_won": s.max_loan_won,
            "cash_needed_won": s.cash_needed_won,
            "notes": s.notes,
            "is_range_note": s.is_range_note,
            "rule_ids": json.loads(s.rule_ids_json or "[]"),
        }
        for s in item.loan_scenarios
    ]
    ladder = cash_ladder(loan_rows, cost.total_cost_won)

    return {
        "id": item.id,
        "source": item.source,
        "title": item.title,
        "address": item.address,
        "usage": item.usage,
        "case_no": item.case_no,
        "court_or_org": item.court_or_org,
        "source_url": item.source_url,
        "notes": item.notes,
        "lot_id": item.lot_id,
        "appraisal": triple_dict(item.appraisal_won),
        "min_bid": triple_dict(item.min_bid_won),
        "planned_price": triple_dict(item.planned_price_won),
        "digit_warnings": digit_warn,
        "verdict": latest.verdict if latest else "HOLD",
        "lat": item.lat,
        "lng": item.lng,
        "created_at": item.created_at,
        "finance": {
            "bid_won": fin.bid_won if fin else None,
            "assume_deposit_won": fin.assume_deposit_won if fin else 0,
            "assume_other_rights_won": fin.assume_other_rights_won if fin else 0,
            "acquisition_tax_won": fin.acquisition_tax_won if fin else 0,
            "vat_won": fin.vat_won if fin else 0,
            "registry_legal_won": fin.registry_legal_won if fin else 0,
            "unpaid_mgmt_won": fin.unpaid_mgmt_won if fin else 0,
            "repair_won": fin.repair_won if fin else 0,
            "eviction_won": fin.eviction_won if fin else 0,
            "loan_interest_won": fin.loan_interest_won if fin else 0,
            "disposal_cost_won": fin.disposal_cost_won if fin else 0,
            "contingency_won": fin.contingency_won if fin else 0,
            "conservative_exit_won": fin.conservative_exit_won if fin else None,
            "target_margin_ratio": fin.target_margin_ratio if fin else 0.15,
        },
        "cost_breakdown": cost.to_dict(),
        "bid_ceiling": ceiling,
        "loan_scenarios": loan_rows,
        "cash_ladder": ladder,
        "loan_disclaimer": (
            "대출·필요현금은 RuleConfig 기반 가정 범위입니다. "
            "AI/시스템이 입찰이나 대출 승인을 결정하지 않습니다."
        ),
        "what_if": what_if,
        "missing_docs": missing,
        "beginner_ban": (latest.verdict == "BEGINNER_BAN") if latest else True,
        "check_next": check_next,
        "rights_status_note": (
            "필수 문서 부족 — 권리 확정 금지 (UNKNOWN/HOLD)."
            if missing
            else "문서 근거가 있는 권리만 확정하세요."
        ),
        "documents": [
            {
                "id": d.id,
                "doc_type": d.doc_type,
                "filename": d.filename,
                "page_count": d.page_count,
                "masked": bool(d.masked),
                "classify_confidence": getattr(d, "classify_confidence", 0) or 0,
                "classify_note": getattr(d, "classify_note", "") or "",
                "user_corrected": bool(d.user_corrected),
                "confirmed_at": d.confirmed_at.isoformat() if d.confirmed_at else None,
                "text_preview": (d.extracted_text or "")[:300],
            }
            for d in item.documents
        ],
        "rights": [
            {
                "id": r.id,
                "kind": r.kind,
                "label": r.label,
                "amount_won": r.amount_won,
                "priority_hint": r.priority_hint,
                "event_date": r.event_date.isoformat() if r.event_date else None,
                "is_malso_baseline": bool(getattr(r, "is_malso_baseline", 0)),
                "status": r.status,
                "evidence_doc_id": r.evidence_doc_id,
                "evidence_page": r.evidence_page,
                "evidence_excerpt": r.evidence_excerpt,
                "confirmed_at": r.confirmed_at.isoformat() if r.confirmed_at else None,
                "rule_track": r.rule_track,
                "notes": r.notes,
            }
            for r in item.rights
        ],
        "occupancies": [
            {
                "id": c.id,
                "claim_kind": c.claim_kind,
                "occupant_label": c.occupant_label,
                "deposit_won": c.deposit_won,
                "monthly_rent_won": c.monthly_rent_won,
                "move_in_date": c.move_in_date.isoformat() if c.move_in_date else None,
                "fixed_date": c.fixed_date.isoformat() if c.fixed_date else None,
                "business_reg_date": c.business_reg_date.isoformat()
                if c.business_reg_date
                else None,
                "tax_invoice_ok": c.tax_invoice_ok,
                "status": c.status,
                "evidence_doc_id": c.evidence_doc_id,
                "evidence_page": c.evidence_page,
                "evidence_excerpt": c.evidence_excerpt,
                "confirmed_at": c.confirmed_at.isoformat() if c.confirmed_at else None,
                "notes": c.notes,
            }
            for c in item.occupancies
        ],
        "timeline_eval": apply_evaluation(item, docs_ok=not bool(missing), persist=False),
        "tabs_hint": [
            "overview",
            "rights",
            "loan_cash",
            "market",
            "docs",
            "site",
            "guide",
        ],
    }


async def apply_acquisition_tax_from_rules(
    session: AsyncSession,
    item_id: int,
) -> AuctionItem:
    """Fill acquisition_tax_won from RuleConfig rate × bid (not a tax ruling)."""
    await seed_rules(session)
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    fin = item.finance
    if fin is None:
        fin = FinanceProfile(item_id=item.id, bid_won=item.min_bid_won)
        session.add(fin)
        await session.flush()
    bucket = usage_bucket(item.usage)
    tax_key = (
        "acquisition_tax_rate_commercial"
        if bucket == "상가"
        else "acquisition_tax_rate_housing"
    )
    rule = await get_rule(
        session,
        tax_key,
        region_code=item.region_code or "*",
        usage=bucket,
    )
    ref = rule_ref_from_model(rule, rule_key=tax_key)
    if ref is None or not ref.value.get("rate"):
        raise ValueError(f"RuleConfig {tax_key} 없음 — 취득세 UNKNOWN")
    rate = float(ref.value["rate"])
    base = fin.bid_won or item.min_bid_won or item.planned_price_won or 0
    if not base:
        raise ValueError("낙찰가/최저가 없어 취득세 산출 불가")
    tax = estimate_acquisition_tax_won(tax_base_won=int(base), rate=rate)
    fin.acquisition_tax_won = tax
    await session.commit()
    return await recompute(session, item_id)


async def preview_what_if(
    session: AsyncSession,
    item_id: int,
    *,
    assume_deposit_factor: float = 1.0,
    eviction_extra_won: int = 0,
    loan_haircut_won: int = 0,
    exit_drop_ratio: float = 0.0,
) -> dict:
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    fin = item.finance
    bid = (fin.bid_won if fin else None) or item.min_bid_won or 0
    cost = compute_total_cost(
        bid_won=bid or 0,
        assume_deposit_won=fin.assume_deposit_won if fin else 0,
        assume_other_rights_won=fin.assume_other_rights_won if fin else 0,
        acquisition_tax_won=fin.acquisition_tax_won if fin else 0,
        vat_won=fin.vat_won if fin else 0,
        registry_legal_won=fin.registry_legal_won if fin else 0,
        unpaid_mgmt_won=fin.unpaid_mgmt_won if fin else 0,
        repair_won=fin.repair_won if fin else 0,
        eviction_won=fin.eviction_won if fin else 0,
        loan_interest_won=fin.loan_interest_won if fin else 0,
        disposal_cost_won=fin.disposal_cost_won if fin else 0,
        contingency_won=fin.contingency_won if fin else 0,
    )
    exit_won = (fin.conservative_exit_won if fin else None) or item.appraisal_won or 0
    result = custom_what_if(
        cost,
        conservative_exit_won=exit_won,
        target_margin_ratio=fin.target_margin_ratio if fin else 0.15,
        assume_deposit_factor=assume_deposit_factor,
        eviction_extra_won=eviction_extra_won,
        loan_haircut_won=loan_haircut_won,
        exit_drop_ratio=exit_drop_ratio,
    )
    result["disclaimer"] = (
        "What-if는 가정 시나리오입니다. 입찰·대출 승인 결정이 아닙니다."
    )
    return result
