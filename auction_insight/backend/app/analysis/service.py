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
    scenario_adjustments,
)
from app.analysis.models import (
    AnalysisRun,
    AuctionItem,
    FinanceProfile,
    LoanScenario,
)
from app.analysis.money import detect_digit_errors, parse_user_amount, triple_dict
from app.analysis.rules import get_rule, seed_rules
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
    ltv_rule = await get_rule(session, "ltv_cap_housing", usage=item.usage or "주택")
    ltv = {"conservative": 0.0, "base": 0.0, "optimistic": 0.0}
    ltv_note = "LTV RuleConfig 없음 — 대출 한도 UNKNOWN. 금융기관·최신 규제 확인 필요."
    rule_ids: list[int] = []
    if ltv_rule:
        rule_ids.append(ltv_rule.id)
        try:
            ltv = {**ltv, **json.loads(ltv_rule.value_json)}
            ltv_note = ltv_rule.source_label
        except json.JSONDecodeError:
            pass

    # clear old scenarios
    for old in list(item.loan_scenarios):
        await session.delete(old)
    await session.flush()

    exit_won = fin.conservative_exit_won or item.appraisal_won or 0
    for label in ("conservative", "base", "optimistic"):
        rate = float(ltv.get(label) or 0)
        max_loan = int(round(exit_won * rate)) if exit_won and rate else None
        cash = None if max_loan is None else max(0, cost.total_cost_won - max_loan)
        session.add(
            LoanScenario(
                item_id=item.id,
                label=label,
                max_loan_won=max_loan,
                cash_needed_won=cash,
                rule_ids_json=json.dumps(rule_ids),
                notes=ltv_note,
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
        check_next.append("등기 갑·을구 권리를 문서 근거와 함께 입력하세요.")
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
    what_if = {
        "partial_deposit": scenario_adjustments(
            cost,
            assume_deposit_factor=0.5,
            conservative_exit_won=exit_won or None,
            target_margin_ratio=fin.target_margin_ratio if fin else 0.15,
        ),
        "full_deposit": scenario_adjustments(
            cost,
            assume_deposit_factor=1.0,
            conservative_exit_won=exit_won or None,
            target_margin_ratio=fin.target_margin_ratio if fin else 0.15,
        ),
        "eviction_delay": scenario_adjustments(
            cost,
            eviction_extra_won=5_000_000,
            conservative_exit_won=exit_won or None,
            target_margin_ratio=fin.target_margin_ratio if fin else 0.15,
        ),
        "loan_haircut": scenario_adjustments(
            cost,
            loan_haircut_won=50_000_000,
            conservative_exit_won=exit_won or None,
            target_margin_ratio=fin.target_margin_ratio if fin else 0.15,
        ),
        "exit_drop_10pct": scenario_adjustments(
            cost,
            exit_drop_ratio=0.10,
            conservative_exit_won=exit_won or None,
            target_margin_ratio=fin.target_margin_ratio if fin else 0.15,
        ),
    }
    missing = json.loads(latest.missing_docs_json) if latest else []
    digit_warn = detect_digit_errors(
        appraisal_won=item.appraisal_won,
        min_bid_won=item.min_bid_won,
        planned_price_won=item.planned_price_won,
    )
    check_next = [REQUIRED_DOC_LABELS.get(m, m) for m in missing]
    if fin and fin.acquisition_tax_won == 0:
        check_next.append("취득세 미입력 — RuleConfig·전문가 확인")

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
        "loan_scenarios": [
            {
                "label": s.label,
                "max_loan_won": s.max_loan_won,
                "cash_needed_won": s.cash_needed_won,
                "notes": s.notes,
                "is_range_note": s.is_range_note,
            }
            for s in item.loan_scenarios
        ],
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
            }
            for d in item.documents
        ],
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
