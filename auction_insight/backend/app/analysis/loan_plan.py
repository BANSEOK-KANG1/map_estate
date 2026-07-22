"""Loan & cash-needed planning from RuleConfig (ranges only, never a firm quote)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.analysis.calculator import CostBreakdown, compute_bid_ceiling, scenario_adjustments


SCENARIO_LABELS = ("conservative", "base", "optimistic")


@dataclass
class RuleRef:
    id: int | None
    rule_key: str
    source_label: str
    source_url: str
    effective_from: str
    notes: str
    value: dict

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "rule_key": self.rule_key,
            "source_label": self.source_label,
            "source_url": self.source_url,
            "effective_from": self.effective_from,
            "notes": self.notes,
            "value": self.value,
        }


def parse_rule_value(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}


def rule_ref_from_model(rule: Any | None, *, rule_key: str) -> RuleRef | None:
    if rule is None:
        return None
    return RuleRef(
        id=getattr(rule, "id", None),
        rule_key=getattr(rule, "rule_key", rule_key) or rule_key,
        source_label=getattr(rule, "source_label", "") or "",
        source_url=getattr(rule, "source_url", "") or "",
        effective_from=str(getattr(rule, "effective_from", "") or ""),
        notes=getattr(rule, "notes", "") or "",
        value=parse_rule_value(getattr(rule, "value_json", None)),
    )


def pick_ltv_rates(ltv_value: dict) -> dict[str, float]:
    out = {"conservative": 0.0, "base": 0.0, "optimistic": 0.0}
    for k in out:
        try:
            out[k] = float(ltv_value.get(k) or 0)
        except (TypeError, ValueError):
            out[k] = 0.0
    return out


def estimate_acquisition_tax_won(
    *,
    tax_base_won: int,
    rate: float,
) -> int:
    if tax_base_won <= 0 or rate <= 0:
        return 0
    return int(round(tax_base_won * rate))


def estimate_holding_interest_won(
    *,
    max_loan_won: int,
    annual_rate: float,
    hold_months: float,
) -> int:
    """Rough interest during hold — not a bank quote."""
    if max_loan_won <= 0 or annual_rate <= 0 or hold_months <= 0:
        return 0
    return int(round(max_loan_won * annual_rate * (hold_months / 12.0)))


def build_loan_scenarios(
    *,
    collateral_won: int,
    total_cost_won: int,
    ltv_rates: dict[str, float],
    ltv_rule: RuleRef | None,
    dsr_rule: RuleRef | None,
    interest_rule: RuleRef | None,
    hold_months: float = 6.0,
) -> list[dict]:
    """Conservative / base / optimistic loan + cash-needed ranges."""
    dsr_cap = None
    if dsr_rule and dsr_rule.value:
        try:
            dsr_cap = float(dsr_rule.value.get("cap") or dsr_rule.value.get("base") or 0) or None
        except (TypeError, ValueError):
            dsr_cap = None

    annual_rate = 0.0
    if interest_rule and interest_rule.value:
        try:
            annual_rate = float(interest_rule.value.get("annual_rate") or 0)
        except (TypeError, ValueError):
            annual_rate = 0.0

    rule_ids = [r.id for r in (ltv_rule, dsr_rule, interest_rule) if r and r.id]
    rows: list[dict] = []
    for label in SCENARIO_LABELS:
        rate = float(ltv_rates.get(label) or 0)
        max_loan = int(round(collateral_won * rate)) if collateral_won and rate else None
        cash = None if max_loan is None else max(0, total_cost_won - max_loan)
        interest = (
            estimate_holding_interest_won(
                max_loan_won=max_loan or 0,
                annual_rate=annual_rate,
                hold_months=hold_months,
            )
            if max_loan
            else 0
        )
        notes_parts = []
        if ltv_rule:
            notes_parts.append(f"LTV {label}={rate:.0%} · {ltv_rule.source_label}")
        else:
            notes_parts.append("LTV RuleConfig 없음 — 대출 한도 UNKNOWN")
        if dsr_rule:
            notes_parts.append(
                f"DSR 상한 참고={dsr_cap:.0%}" if dsr_cap else "DSR RuleConfig 있음(소득 미입력)"
            )
            notes_parts.append("연소득 미입력 — DSR 한도는 확정 적용 불가(UNKNOWN)")
        else:
            notes_parts.append("DSR RuleConfig 없음")
        if interest and annual_rate:
            notes_parts.append(
                f"보유 {hold_months:g}개월 이자 러프≈{interest:,}원 (연 {annual_rate:.1%})"
            )
        rows.append(
            {
                "label": label,
                "ltv_rate": rate,
                "max_loan_won": max_loan,
                "cash_needed_won": cash,
                "interest_hint_won": interest or None,
                "dsr_cap": dsr_cap,
                "dsr_status": "UNKNOWN",
                "rule_ids": rule_ids,
                "notes": " · ".join(notes_parts),
                "is_range_note": (
                    "대출은 확정액이 아니라 보수적·기준·낙관적 범위입니다. "
                    "금융기관 심사·최신 규제·담보평가를 확인하세요."
                ),
            }
        )
    return rows


def build_what_if_bundle(
    cost: CostBreakdown,
    *,
    conservative_exit_won: int,
    target_margin_ratio: float,
) -> dict[str, dict]:
    """Fixed what-if pack required by product spec."""
    return {
        "deposit_half": scenario_adjustments(
            cost,
            assume_deposit_factor=0.5,
            conservative_exit_won=conservative_exit_won,
            target_margin_ratio=target_margin_ratio,
        ),
        "deposit_full": scenario_adjustments(
            cost,
            assume_deposit_factor=1.0,
            conservative_exit_won=conservative_exit_won,
            target_margin_ratio=target_margin_ratio,
        ),
        "eviction_delay": scenario_adjustments(
            cost,
            eviction_extra_won=5_000_000,
            conservative_exit_won=conservative_exit_won,
            target_margin_ratio=target_margin_ratio,
        ),
        "loan_cut_20pct": scenario_adjustments(
            cost,
            loan_haircut_won=int(round(cost.bid_won * 0.2)),
            conservative_exit_won=conservative_exit_won,
            target_margin_ratio=target_margin_ratio,
        ),
        "exit_drop_10pct": scenario_adjustments(
            cost,
            exit_drop_ratio=0.10,
            conservative_exit_won=conservative_exit_won,
            target_margin_ratio=target_margin_ratio,
        ),
    }


def custom_what_if(
    cost: CostBreakdown,
    *,
    conservative_exit_won: int,
    target_margin_ratio: float,
    assume_deposit_factor: float = 1.0,
    eviction_extra_won: int = 0,
    loan_haircut_won: int = 0,
    exit_drop_ratio: float = 0.0,
) -> dict:
    return scenario_adjustments(
        cost,
        assume_deposit_factor=assume_deposit_factor,
        eviction_extra_won=eviction_extra_won,
        loan_haircut_won=loan_haircut_won,
        exit_drop_ratio=exit_drop_ratio,
        conservative_exit_won=conservative_exit_won,
        target_margin_ratio=target_margin_ratio,
    )


def cash_ladder(scenarios: list[dict], total_cost_won: int) -> dict:
    """Summarize cash needed across ranges for UI."""
    values = [s.get("cash_needed_won") for s in scenarios if s.get("cash_needed_won") is not None]
    loans = [s.get("max_loan_won") for s in scenarios if s.get("max_loan_won") is not None]
    return {
        "total_cost_won": total_cost_won,
        "cash_needed_min_won": min(values) if values else None,
        "cash_needed_max_won": max(values) if values else None,
        "loan_min_won": min(loans) if loans else None,
        "loan_max_won": max(loans) if loans else None,
        "note": "필요현금 = 총투입액 − 시나리오별 대출한도(가정). 확정 견적 아님.",
    }
