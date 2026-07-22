"""Pydantic schemas for analysis module."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class MoneyTripleOut(BaseModel):
    won: int
    manwon: float
    eok: float
    label_won: str
    label_manwon: str
    label_eok: str


class MoneyValidateIn(BaseModel):
    appraisal_won: int | None = None
    min_bid_won: int | None = None
    planned_price_won: int | None = None
    # alternate unit inputs
    appraisal_manwon: float | None = None
    min_bid_manwon: float | None = None
    planned_price_manwon: float | None = None


class MoneyValidateOut(BaseModel):
    appraisal: MoneyTripleOut | None = None
    min_bid: MoneyTripleOut | None = None
    planned_price: MoneyTripleOut | None = None
    warnings: list[dict[str, str]] = Field(default_factory=list)


class AuctionItemCreate(BaseModel):
    source: str  # court | onbid
    title: str = ""
    address: str
    usage: str = ""
    case_no: str = ""
    court_or_org: str = ""
    external_id: str = ""
    lot_id: int | None = None
    appraisal_won: int | None = None
    min_bid_won: int | None = None
    planned_price_won: int | None = None
    appraisal_manwon: float | None = None
    min_bid_manwon: float | None = None
    planned_price_manwon: float | None = None
    fail_count: int = 0
    lat: float | None = None
    lng: float | None = None
    source_url: str = ""
    notes: str = ""


class FinanceUpdate(BaseModel):
    bid_won: int | None = None
    assume_deposit_won: int | None = None
    assume_other_rights_won: int | None = None
    acquisition_tax_won: int | None = None
    vat_won: int | None = None
    registry_legal_won: int | None = None
    unpaid_mgmt_won: int | None = None
    repair_won: int | None = None
    eviction_won: int | None = None
    loan_interest_won: int | None = None
    disposal_cost_won: int | None = None
    contingency_won: int | None = None
    conservative_exit_won: int | None = None
    target_margin_ratio: float | None = None


class AuctionItemSummary(BaseModel):
    id: int
    source: str
    title: str
    address: str
    usage: str
    case_no: str
    appraisal: MoneyTripleOut | None = None
    min_bid: MoneyTripleOut | None = None
    planned_price: MoneyTripleOut | None = None
    digit_warnings: list[dict[str, str]] = Field(default_factory=list)
    verdict: str = "HOLD"
    lat: float | None = None
    lng: float | None = None
    created_at: datetime | None = None


class AuctionItemDetail(AuctionItemSummary):
    court_or_org: str = ""
    source_url: str = ""
    notes: str = ""
    lot_id: int | None = None
    finance: dict = Field(default_factory=dict)
    cost_breakdown: dict = Field(default_factory=dict)
    bid_ceiling: dict | None = None
    loan_scenarios: list[dict] = Field(default_factory=list)
    what_if: dict = Field(default_factory=dict)
    missing_docs: list[str] = Field(default_factory=list)
    beginner_ban: bool = False
    check_next: list[str] = Field(default_factory=list)
    rights_status_note: str = ""
    documents: list[dict] = Field(default_factory=list)
    tabs_hint: list[str] = Field(
        default_factory=lambda: [
            "overview",
            "rights",
            "loan_cash",
            "market",
            "docs",
            "site",
            "guide",
        ]
    )


class RuleOut(BaseModel):
    id: int
    rule_key: str
    effective_from: str
    region_code: str
    usage: str
    value_json: str
    source_url: str
    source_label: str
    notes: str


class DocumentCorrectIn(BaseModel):
    doc_type: str | None = None
    extracted_text: str | None = None
    confirm: bool = False


class EvidenceIn(BaseModel):
    page: int = 1
    query: str = ""


class RightFromEvidenceIn(BaseModel):
    doc_id: int
    page: int = 1
    label: str = ""
    kind: str = "other"
    query: str = ""
    amount_won: int | None = None
    event_date: str | None = None
    is_malso_baseline: bool = False


class RightCreateIn(BaseModel):
    kind: str = "other"
    label: str = ""
    amount_won: int | None = None
    priority_hint: int | None = None
    event_date: str | None = None
    is_malso_baseline: bool = False
    status: str | None = None
    evidence_doc_id: int | None = None
    evidence_page: int | None = None
    evidence_excerpt: str = ""
    rule_track: str | None = None
    notes: str = ""
    confirm: bool = False


class RightPatchIn(BaseModel):
    kind: str | None = None
    label: str | None = None
    amount_won: int | None = None
    priority_hint: int | None = None
    event_date: str | None = None
    is_malso_baseline: bool | None = None
    status: str | None = None
    evidence_doc_id: int | None = None
    evidence_page: int | None = None
    evidence_excerpt: str | None = None
    rule_track: str | None = None
    notes: str | None = None
    confirm: bool = False


class OccupancyCreateIn(BaseModel):
    claim_kind: str = "housing"  # housing | commercial
    occupant_label: str = ""
    deposit_won: int | None = None
    monthly_rent_won: int | None = None
    move_in_date: str | None = None
    fixed_date: str | None = None
    business_reg_date: str | None = None
    tax_invoice_ok: int | None = None
    evidence_doc_id: int | None = None
    evidence_page: int | None = None
    evidence_excerpt: str = ""
    notes: str = ""


class OccupancyPatchIn(BaseModel):
    claim_kind: str | None = None
    occupant_label: str | None = None
    deposit_won: int | None = None
    monthly_rent_won: int | None = None
    move_in_date: str | None = None
    fixed_date: str | None = None
    business_reg_date: str | None = None
    tax_invoice_ok: int | None = None
    status: str | None = None
    evidence_doc_id: int | None = None
    evidence_page: int | None = None
    evidence_excerpt: str | None = None
    notes: str | None = None
    confirm: bool = False


class TimelineEvaluateIn(BaseModel):
    apply_finance_suggest: bool = False
