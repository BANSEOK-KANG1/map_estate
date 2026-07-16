from datetime import date, datetime

from sqlalchemy import (
    Boolean,
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
    sido: Mapped[str] = mapped_column(String(32), nullable=False, default="서울특별시")


class Complex(Base):
    """건물/매물 단위 (오피스텔·빌라·다가구) + 호가형 데모 메타."""

    __tablename__ = "complexes"
    __table_args__ = (
        UniqueConstraint(
            "region_code",
            "dong",
            "jibun",
            "name",
            "housing_type",
            name="uq_complex_key",
        ),
        Index("ix_complex_region", "region_code"),
        Index("ix_complex_name", "name"),
        Index("ix_complex_housing", "housing_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_code: Mapped[str] = mapped_column(String(5), ForeignKey("regions.code"), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    housing_type: Mapped[str] = mapped_column(String(16), nullable=False, default="officetel")
    dong: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    jibun: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    road_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    build_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    geocoded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Listing-style demo enrichments
    facing: Mapped[str] = mapped_column(String(16), nullable=False, default="")  # 남향/남동향...
    move_in_ok: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # 전입신고
    loan_manwon: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 융자(만원)
    room_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bath_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parking: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    agent_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    agent_phone: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    agent_office: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    photo_urls: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON list
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    listed_at: Mapped[date | None] = mapped_column(Date, nullable=True)  # 매물 수집/게시 기준일

    trades: Mapped[list["Trade"]] = relationship(back_populates="complex")
    region: Mapped["Region"] = relationship()


class Trade(Base):
    __tablename__ = "trades"
    __table_args__ = (
        UniqueConstraint(
            "complex_id",
            "deal_date",
            "deal_kind",
            "exclusive_area",
            "floor",
            "price_manwon",
            "monthly_rent_manwon",
            name="uq_trade",
        ),
        Index("ix_trade_complex_date", "complex_id", "deal_date"),
        Index("ix_trade_deal_ym", "deal_year", "deal_month"),
        Index("ix_trade_kind", "deal_kind"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_id: Mapped[int] = mapped_column(Integer, ForeignKey("complexes.id"), nullable=False)
    deal_date: Mapped[date] = mapped_column(Date, nullable=False)
    deal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    deal_month: Mapped[int] = mapped_column(Integer, nullable=False)
    deal_kind: Mapped[str] = mapped_column(String(8), nullable=False, default="sale")
    exclusive_area: Mapped[float] = mapped_column(Float, nullable=False)
    price_manwon: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_rent_manwon: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    floor: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dealing_gbn: Mapped[str] = mapped_column(String(32), nullable=False, default="")

    complex: Mapped["Complex"] = relationship(back_populates="trades")


class PoiCache(Base):
    __tablename__ = "poi_cache"
    __table_args__ = (UniqueConstraint("complex_id", "category", name="uq_poi_cache"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    complex_id: Mapped[int] = mapped_column(Integer, ForeignKey("complexes.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nearest_distance_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    payload_json: Mapped[str] = mapped_column(String, nullable=False, default="[]")
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class IngestRun(Base):
    __tablename__ = "ingest_runs"
    __table_args__ = (
        UniqueConstraint(
            "region_code",
            "deal_ym",
            "housing_type",
            "deal_kind",
            name="uq_ingest_run",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    region_code: Mapped[str] = mapped_column(String(5), nullable=False)
    deal_ym: Mapped[str] = mapped_column(String(6), nullable=False)
    housing_type: Mapped[str] = mapped_column(String(16), nullable=False, default="officetel")
    deal_kind: Mapped[str] = mapped_column(String(8), nullable=False, default="sale")
    trade_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ok")
    message: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    finished_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
