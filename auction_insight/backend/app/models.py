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


class Region(Base):
    __tablename__ = "regions"

    code: Mapped[str] = mapped_column(String(5), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    sido: Mapped[str] = mapped_column(String(32), nullable=False)


class AuctionLot(Base):
    """경매·공매 물건."""

    __tablename__ = "auction_lots"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_lot_source_ext"),
        Index("ix_lot_region", "region_code"),
        Index("ix_lot_source", "source"),
        Index("ix_lot_status", "status"),
        Index("ix_lot_bid_end", "bid_end_at"),
        Index("ix_lot_coords", "lat", "lng"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(16), nullable=False)  # onbid | court
    external_id: Mapped[str] = mapped_column(String(64), nullable=False)
    case_no: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    court_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    title: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    usage: Mapped[str] = mapped_column(String(64), nullable=False, default="")  # 아파트/오피스텔…
    address: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    region_code: Mapped[str | None] = mapped_column(
        String(5), ForeignKey("regions.code"), nullable=True
    )
    dong: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    exclusive_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    land_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    build_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_info: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    appraisal_manwon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_bid_manwon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    bid_start_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    bid_end_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_url: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    photo_urls: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    pbct_cdtn_no: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    detail_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # Cached insight fields (updated on enrich)
    market_median_manwon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    market_sample_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    market_pyeong_manwon: Mapped[float | None] = mapped_column(Float, nullable=True)
    market_note: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    station_line: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    discount_vs_appraisal: Mapped[float | None] = mapped_column(Float, nullable=True)
    discount_vs_market: Mapped[float | None] = mapped_column(Float, nullable=True)
    infra_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    urgency_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    nearest_station: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    station_walk_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    region: Mapped["Region | None"] = relationship()
    schedules: Mapped[list["AuctionSchedule"]] = relationship(
        back_populates="lot", cascade="all, delete-orphan"
    )
    pois: Mapped[list["PoiCache"]] = relationship(
        back_populates="lot", cascade="all, delete-orphan"
    )


class AuctionSchedule(Base):
    __tablename__ = "auction_schedules"
    __table_args__ = (
        UniqueConstraint("lot_id", "round_no", name="uq_schedule_round"),
        Index("ix_schedule_lot", "lot_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(Integer, ForeignKey("auction_lots.id"), nullable=False)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    sale_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    min_bid_manwon: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str] = mapped_column(String(32), nullable=False, default="")  # 유찰/매각/진행
    note: Mapped[str] = mapped_column(String(256), nullable=False, default="")

    lot: Mapped["AuctionLot"] = relationship(back_populates="schedules")


class PoiCache(Base):
    __tablename__ = "poi_cache"
    __table_args__ = (UniqueConstraint("lot_id", "category", name="uq_poi_lot_cat"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(Integer, ForeignKey("auction_lots.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nearest_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    lot: Mapped["AuctionLot"] = relationship(back_populates="pois")


class NearbyTrade(Base):
    """인근 실거래 표본 (시세 비교용 캐시)."""

    __tablename__ = "nearby_trades"
    __table_args__ = (
        Index("ix_nearby_lot", "lot_id"),
        Index("ix_nearby_region", "region_code", "deal_ym"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lot_id: Mapped[int] = mapped_column(Integer, ForeignKey("auction_lots.id"), nullable=False)
    region_code: Mapped[str] = mapped_column(String(5), nullable=False, default="")
    deal_ym: Mapped[str] = mapped_column(String(6), nullable=False, default="")
    housing_type: Mapped[str] = mapped_column(String(16), nullable=False, default="apt")
    address: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    exclusive_area: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    price_manwon: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    deal_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    lot_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    finished_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
