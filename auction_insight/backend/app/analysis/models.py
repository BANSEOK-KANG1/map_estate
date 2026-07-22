"""Analysis-domain SQLAlchemy models (additive; does not replace AuctionLot)."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class AuctionItem(Base):
    """심층 분석용 물건 (수동 등록 또는 AuctionLot 연결)."""

    __tablename__ = "analysis_auction_items"
    __table_args__ = (
        Index("ix_analysis_item_source", "source"),
        Index("ix_analysis_item_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # court | onbid
    external_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    lot_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # optional AuctionLot.id
    case_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    court_or_org: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    usage: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    address: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    region_code: Mapped[str | None] = mapped_column(String(5), nullable=True)
    # Canonical money unit: KRW won (정수)
    appraisal_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_bid_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    planned_price_won: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 공매예정가 등
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    bid_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    documents: Mapped[list[AuctionDocument]] = relationship(back_populates="item")
    rights: Mapped[list[RightEntry]] = relationship(back_populates="item")
    occupancies: Mapped[list[OccupancyClaim]] = relationship(back_populates="item")
    analysis_runs: Mapped[list[AnalysisRun]] = relationship(back_populates="item")
    finance: Mapped[FinanceProfile | None] = relationship(
        back_populates="item", uselist=False
    )
    loan_scenarios: Mapped[list[LoanScenario]] = relationship(back_populates="item")


class AuctionDocument(Base):
    __tablename__ = "analysis_auction_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_auction_items.id"), nullable=False
    )
    doc_type: Mapped[str] = mapped_column(String(64), nullable=False, default="other")
    # registry | appraisal | sale_spec | onbid_notice | other
    filename: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    content_type: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extracted_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pages_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # [{page:1, text:"masked excerpt...", char_count:n}]
    classify_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    classify_note: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    masked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)  # 1 if PII masked
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_corrected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    item: Mapped[AuctionItem] = relationship(back_populates="documents")


class RightEntry(Base):
    """권리 한 건. 문서 근거 없으면 status는 UNKNOWN/HOLD만 허용(서비스 계층)."""

    __tablename__ = "analysis_right_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_auction_items.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # mortgage | seize | lease_reg | tax | other | baseline
    label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    amount_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    priority_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_malso_baseline: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    # UNKNOWN | HOLD | EXTINGUISH | ASSUME | INFO
    evidence_doc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rule_track: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    # court_malso | onbid_tax_distribute | shared
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    item: Mapped[AuctionItem] = relationship(back_populates="rights")


class OccupancyClaim(Base):
    __tablename__ = "analysis_occupancy_claims"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_auction_items.id"), nullable=False
    )
    claim_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="housing")
    # housing | commercial
    occupant_label: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    deposit_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_rent_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # housing-specific
    move_in_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    fixed_date: Mapped[date | None] = mapped_column(Date, nullable=True)  # 확정일자
    # commercial-specific
    business_reg_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tax_invoice_ok: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="UNKNOWN")
    evidence_doc_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_excerpt: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    item: Mapped[AuctionItem] = relationship(back_populates="occupancies")


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_auction_items.id"), nullable=False
    )
    verdict: Mapped[str] = mapped_column(String(32), nullable=False, default="HOLD")
    # REVIEW_OK | REVIEW_CONDITIONAL | HOLD | BEGINNER_BAN
    missing_docs_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    total_cost_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bid_ceiling_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    item: Mapped[AuctionItem] = relationship(back_populates="analysis_runs")


class FinanceProfile(Base):
    __tablename__ = "analysis_finance_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_auction_items.id"), unique=True, nullable=False
    )
    bid_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assume_deposit_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    assume_other_rights_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    acquisition_tax_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    vat_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    registry_legal_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unpaid_mgmt_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    repair_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eviction_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loan_interest_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    disposal_cost_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    contingency_won: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    conservative_exit_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_margin_ratio: Mapped[float] = mapped_column(Float, nullable=False, default=0.15)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    item: Mapped[AuctionItem] = relationship(back_populates="finance")


class LoanScenario(Base):
    __tablename__ = "analysis_loan_scenarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("analysis_auction_items.id"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(32), nullable=False, default="base")
    # conservative | base | optimistic
    max_loan_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cash_needed_won: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rule_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 확정액 아님 — 범위 안내
    is_range_note: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        default="대출은 확정액이 아니라 가정 범위입니다. 금융기관 심사가 필요합니다.",
    )

    item: Mapped[AuctionItem] = relationship(back_populates="loan_scenarios")


class RuleConfig(Base):
    """LTV/DSR/취득세 등 — 하드코딩 금지, 적용일·출처 필수."""

    __tablename__ = "analysis_rule_configs"
    __table_args__ = (
        UniqueConstraint(
            "rule_key",
            "effective_from",
            "region_code",
            "usage",
            name="uq_rule_key_eff_region_usage",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_key: Mapped[str] = mapped_column(String(64), nullable=False)
    # acquisition_tax_rate | ltv_cap | dsr_cap | ...
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    region_code: Mapped[str] = mapped_column(String(16), nullable=False, default="*")
    usage: Mapped[str] = mapped_column(String(64), nullable=False, default="*")
    value_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    source_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    source_label: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
