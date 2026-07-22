"""Deterministic cost & bid-ceiling calculator (no LLM)."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class CostBreakdown:
    bid_won: int
    assume_deposit_won: int
    assume_other_rights_won: int
    acquisition_tax_won: int
    vat_won: int
    registry_legal_won: int
    unpaid_mgmt_won: int
    repair_won: int
    eviction_won: int
    loan_interest_won: int
    disposal_cost_won: int
    contingency_won: int

    @property
    def costs_excluding_bid(self) -> int:
        return (
            self.assume_deposit_won
            + self.assume_other_rights_won
            + self.acquisition_tax_won
            + self.vat_won
            + self.registry_legal_won
            + self.unpaid_mgmt_won
            + self.repair_won
            + self.eviction_won
            + self.loan_interest_won
            + self.disposal_cost_won
            + self.contingency_won
        )

    @property
    def total_cost_won(self) -> int:
        return self.bid_won + self.costs_excluding_bid

    def to_dict(self) -> dict:
        d = asdict(self)
        d["costs_excluding_bid_won"] = self.costs_excluding_bid
        d["total_cost_won"] = self.total_cost_won
        return d


def compute_total_cost(**kwargs: int) -> CostBreakdown:
    return CostBreakdown(
        bid_won=int(kwargs.get("bid_won") or 0),
        assume_deposit_won=int(kwargs.get("assume_deposit_won") or 0),
        assume_other_rights_won=int(kwargs.get("assume_other_rights_won") or 0),
        acquisition_tax_won=int(kwargs.get("acquisition_tax_won") or 0),
        vat_won=int(kwargs.get("vat_won") or 0),
        registry_legal_won=int(kwargs.get("registry_legal_won") or 0),
        unpaid_mgmt_won=int(kwargs.get("unpaid_mgmt_won") or 0),
        repair_won=int(kwargs.get("repair_won") or 0),
        eviction_won=int(kwargs.get("eviction_won") or 0),
        loan_interest_won=int(kwargs.get("loan_interest_won") or 0),
        disposal_cost_won=int(kwargs.get("disposal_cost_won") or 0),
        contingency_won=int(kwargs.get("contingency_won") or 0),
    )


def compute_bid_ceiling(
    *,
    conservative_exit_won: int,
    target_margin_ratio: float,
    costs_excluding_bid_won: int,
    assume_amount_won: int,
    finance_cost_won: int,
) -> dict:
    """
    적정 입찰 상한 =
      보수적 처분가
      - 목표 안전마진
      - 낙찰가 외 비용
      - 인수예상액
      - 금융비용
    """
    margin = int(round(conservative_exit_won * target_margin_ratio))
    ceiling = (
        conservative_exit_won
        - margin
        - costs_excluding_bid_won
        - assume_amount_won
        - finance_cost_won
    )
    return {
        "conservative_exit_won": conservative_exit_won,
        "target_margin_ratio": target_margin_ratio,
        "margin_won": margin,
        "costs_excluding_bid_won": costs_excluding_bid_won,
        "assume_amount_won": assume_amount_won,
        "finance_cost_won": finance_cost_won,
        "bid_ceiling_won": ceiling,
        "formula": (
            "보수적처분가 - 목표안전마진 - 낙찰가외비용 - 인수예상액 - 금융비용"
        ),
    }


def scenario_adjustments(
    base: CostBreakdown,
    *,
    assume_deposit_factor: float = 1.0,
    eviction_extra_won: int = 0,
    loan_haircut_won: int = 0,
    exit_drop_ratio: float = 0.0,
    conservative_exit_won: int | None = None,
    target_margin_ratio: float = 0.15,
) -> dict:
    """What-if: partial/full deposit assume, eviction delay, loan cut, exit drop."""
    adj = CostBreakdown(
        bid_won=base.bid_won,
        assume_deposit_won=int(round(base.assume_deposit_won * assume_deposit_factor)),
        assume_other_rights_won=base.assume_other_rights_won,
        acquisition_tax_won=base.acquisition_tax_won,
        vat_won=base.vat_won,
        registry_legal_won=base.registry_legal_won,
        unpaid_mgmt_won=base.unpaid_mgmt_won,
        repair_won=base.repair_won,
        eviction_won=base.eviction_won + eviction_extra_won,
        loan_interest_won=base.loan_interest_won,
        disposal_cost_won=base.disposal_cost_won,
        contingency_won=base.contingency_won,
    )
    exit_won = conservative_exit_won or 0
    if exit_won and exit_drop_ratio:
        exit_won = int(round(exit_won * (1 - exit_drop_ratio)))
    ceiling = None
    if exit_won:
        assume = adj.assume_deposit_won + adj.assume_other_rights_won
        # costs excluding bid and excluding assume (already separated in formula)
        costs_ex_bid_ex_assume = (
            adj.costs_excluding_bid - adj.assume_deposit_won - adj.assume_other_rights_won
        )
        ceiling = compute_bid_ceiling(
            conservative_exit_won=exit_won,
            target_margin_ratio=target_margin_ratio,
            costs_excluding_bid_won=costs_ex_bid_ex_assume,
            assume_amount_won=assume,
            finance_cost_won=adj.loan_interest_won,
        )
        # cash need rises if loan haircut
        ceiling["extra_cash_from_loan_haircut_won"] = loan_haircut_won
        ceiling["cash_needed_hint_won"] = max(
            0, adj.total_cost_won - (base.bid_won - loan_haircut_won)  # rough
        )
    return {
        "cost": adj.to_dict(),
        "ceiling": ceiling,
        "params": {
            "assume_deposit_factor": assume_deposit_factor,
            "eviction_extra_won": eviction_extra_won,
            "loan_haircut_won": loan_haircut_won,
            "exit_drop_ratio": exit_drop_ratio,
        },
    }
