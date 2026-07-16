"""국토부 오피스텔·연립다세대·단독다가구 실거래(매매/전월세) 수집."""

from __future__ import annotations

import logging
from calendar import monthrange
from datetime import date, datetime
from typing import Any
from xml.etree.ElementTree import Element

import httpx
from defusedxml import ElementTree as ET
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.data.seoul_regions import SEOUL_REGIONS
from app.models import Complex, IngestRun, Region, Trade

logger = logging.getLogger(__name__)

# housing_type + deal_kind → endpoint
SOURCES: dict[tuple[str, str], str] = {
    ("officetel", "sale"): (
        "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"
    ),
    ("officetel", "rent"): (
        "https://apis.data.go.kr/1613000/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent"
    ),
    ("villa", "sale"): (
        "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"
    ),
    ("villa", "rent"): (
        "https://apis.data.go.kr/1613000/RTMSDataSvcRHRent/getRTMSDataSvcRHRent"
    ),
    ("multi", "sale"): (
        "https://apis.data.go.kr/1613000/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade"
    ),
    ("multi", "rent"): (
        "https://apis.data.go.kr/1613000/RTMSDataSvcSHRent/getRTMSDataSvcSHRent"
    ),
}

HOUSING_LABELS = {
    "officetel": "오피스텔",
    "villa": "연립·다세대",
    "multi": "단독·다가구",
}

DEFAULT_SOURCES = [
    ("officetel", "rent"),
    ("officetel", "sale"),
]


def _text(el: Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text.strip()


def _parse_price(raw: str) -> int:
    return int(raw.replace(",", "").replace(" ", "") or "0")


def _first_text(item: Element, tags: list[str], default: str = "") -> str:
    for tag in tags:
        val = _text(item.find(tag))
        if val:
            return val
    return default


def _month_range(months: int) -> list[str]:
    today = date.today()
    y, m = today.year, today.month
    # 실거래 공개는 보통 1~2개월 지연 → 직전월부터 역으로
    m -= 1
    if m == 0:
        m = 12
        y -= 1
    result: list[str] = []
    for _ in range(months):
        result.append(f"{y:04d}{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(result))


def _parse_item(item: Element, housing_type: str, deal_kind: str) -> dict[str, Any] | None:
    year = int(_first_text(item, ["dealYear", "년"]) or "0")
    month = int(_first_text(item, ["dealMonth", "월"]) or "0")
    day = int(_first_text(item, ["dealDay", "일"]) or "1")
    if not year or not month:
        return None
    day = max(1, min(day, monthrange(year, month)[1]))

    name = _first_text(
        item,
        ["offiNm", "mhouseNm", "aptNm", "houseType", "빌딩명", "건물명"],
    )
    dong = _first_text(item, ["umdNm", "dong", "법정동"])
    jibun = _first_text(item, ["jibun", "지번"])
    if not name:
        name = f"{dong} {jibun}".strip() or HOUSING_LABELS.get(housing_type, "매물")

    area_raw = _first_text(
        item,
        ["excluUseAr", "totalFloorAr", "plottageAr", "전용면적", "연면적", "대지면적"],
    )
    try:
        area = float(area_raw or "0")
    except ValueError:
        area = 0.0

    if deal_kind == "rent":
        deposit = _parse_price(_first_text(item, ["deposit", "보증금액", "보증금"]))
        monthly = _parse_price(_first_text(item, ["monthlyRent", "월세금액", "월세"]))
        price = deposit
    else:
        price = _parse_price(_first_text(item, ["dealAmount", "거래금액"]))
        monthly = 0

    floor_raw = _first_text(item, ["floor", "층"])
    try:
        floor = int(floor_raw) if floor_raw else None
    except ValueError:
        floor = None

    build_raw = _first_text(item, ["buildYear", "건축년도"])
    try:
        build_year = int(build_raw) if build_raw else None
    except ValueError:
        build_year = None

    return {
        "name": name,
        "dong": dong,
        "jibun": jibun,
        "road_nm": _first_text(item, ["roadNm", "도로명"]),
        "exclu_use_ar": area,
        "deal_amount": price,
        "monthly_rent": monthly,
        "floor": floor,
        "build_year": build_year,
        "deal_date": date(year, month, day),
        "deal_year": year,
        "deal_month": month,
        "dealing_gbn": _first_text(item, ["dealingGbn", "거래유형"]),
        "housing_type": housing_type,
        "deal_kind": deal_kind,
    }


async def seed_regions(session: AsyncSession) -> None:
    for r in SEOUL_REGIONS:
        existing = await session.get(Region, r["code"])
        if existing is None:
            session.add(Region(code=r["code"], name=r["name"], sido=r["sido"]))
    await session.commit()


async def fetch_page(
    client: httpx.AsyncClient,
    settings: Settings,
    url: str,
    region_code: str,
    deal_ym: str,
    page_no: int = 1,
    num_of_rows: int = 1000,
) -> tuple[list[Element], int]:
    params = {
        "serviceKey": settings.molit_service_key,
        "LAWD_CD": region_code,
        "DEAL_YMD": deal_ym,
        "pageNo": str(page_no),
        "numOfRows": str(num_of_rows),
    }
    resp = await client.get(url, params=params, timeout=60.0)
    if resp.status_code in (401, 403):
        raise RuntimeError(
            "MOLIT 인증 실패(HTTP "
            f"{resp.status_code}). "
            "data.go.kr 인증키 발급현황의 '일반 인증키(Decoding)'인지, "
            "오피스텔 전월세(RTMSDataSvcOffiRent) 활용신청이 승인·반영됐는지 확인하세요. "
            "승인 직후엔 최대 1~2시간 지연될 수 있습니다."
        )
    resp.raise_for_status()
    # Gateway sometimes returns 200 + XML error envelope
    if b"SERVICE_KEY_IS_NOT_REGISTERED" in resp.content or b"Unauthorized" in resp.content[:200]:
        raise RuntimeError(
            "MOLIT serviceKey 미등록/권한 없음. "
            "오피스텔 전월세 API 활용신청 승인 후 Decoding 키를 .env에 넣으세요."
        )
    root = ET.fromstring(resp.content)
    header = root.find(".//header")
    result_code = _text(header.find("resultCode") if header is not None else None)
    result_msg = _text(header.find("resultMsg") if header is not None else None)
    if result_code and result_code not in ("00", "0", "000", "0000"):
        raise RuntimeError(f"MOLIT error {result_code}: {result_msg}")

    total_count = int(_text(root.find(".//body/totalCount"), "0") or "0")
    items = root.findall(".//body/items/item")
    return items, total_count


async def _get_or_create_complex(
    session: AsyncSession,
    region_code: str,
    row: dict,
    cache: dict[tuple, Complex],
) -> Complex:
    key = (region_code, row["dong"], row["jibun"], row["name"], row["housing_type"])
    if key in cache:
        return cache[key]
    result = await session.execute(
        select(Complex).where(
            Complex.region_code == region_code,
            Complex.dong == row["dong"],
            Complex.jibun == row["jibun"],
            Complex.name == row["name"],
            Complex.housing_type == row["housing_type"],
        )
    )
    complex_ = result.scalar_one_or_none()
    if complex_ is None:
        complex_ = Complex(
            region_code=region_code,
            name=row["name"],
            housing_type=row["housing_type"],
            dong=row["dong"],
            jibun=row["jibun"],
            road_name=row["road_nm"],
            build_year=row["build_year"],
        )
        session.add(complex_)
        await session.flush()
    else:
        if row["build_year"] and not complex_.build_year:
            complex_.build_year = row["build_year"]
        if row["road_nm"] and not complex_.road_name:
            complex_.road_name = row["road_nm"]
    cache[key] = complex_
    return complex_


async def ingest_region_month(
    session: AsyncSession,
    settings: Settings,
    region_code: str,
    deal_ym: str,
    housing_type: str,
    deal_kind: str,
    force: bool = False,
) -> int:
    existing = await session.execute(
        select(IngestRun).where(
            IngestRun.region_code == region_code,
            IngestRun.deal_ym == deal_ym,
            IngestRun.housing_type == housing_type,
            IngestRun.deal_kind == deal_kind,
            IngestRun.status == "ok",
        )
    )
    if existing.scalar_one_or_none() and not force:
        return 0

    if not settings.molit_service_key:
        raise RuntimeError("MOLIT_SERVICE_KEY is not configured")

    url = SOURCES[(housing_type, deal_kind)]
    complex_cache: dict[tuple, Complex] = {}
    inserted = 0
    async with httpx.AsyncClient() as client:
        page = 1
        total = None
        while True:
            raw_items, total_count = await fetch_page(
                client, settings, url, region_code, deal_ym, page_no=page
            )
            if total is None:
                total = total_count
            for item in raw_items:
                row = _parse_item(item, housing_type, deal_kind)
                if not row:
                    continue
                if row["deal_amount"] <= 0 and row["monthly_rent"] <= 0:
                    continue
                if row["exclu_use_ar"] <= 0:
                    continue
                # Prefer compact units (원룸·소형)
                if row["exclu_use_ar"] > 85 and housing_type != "multi":
                    continue

                complex_ = await _get_or_create_complex(session, region_code, row, complex_cache)
                dup = await session.execute(
                    select(Trade).where(
                        Trade.complex_id == complex_.id,
                        Trade.deal_date == row["deal_date"],
                        Trade.deal_kind == row["deal_kind"],
                        Trade.exclusive_area == row["exclu_use_ar"],
                        Trade.floor == row["floor"],
                        Trade.price_manwon == row["deal_amount"],
                        Trade.monthly_rent_manwon == row["monthly_rent"],
                    )
                )
                if dup.scalar_one_or_none():
                    continue
                session.add(
                    Trade(
                        complex_id=complex_.id,
                        deal_date=row["deal_date"],
                        deal_year=row["deal_year"],
                        deal_month=row["deal_month"],
                        deal_kind=row["deal_kind"],
                        exclusive_area=row["exclu_use_ar"],
                        price_manwon=row["deal_amount"],
                        monthly_rent_manwon=row["monthly_rent"],
                        floor=row["floor"],
                        dealing_gbn=row["dealing_gbn"],
                    )
                )
                inserted += 1
            if page * 1000 >= (total or 0) or not raw_items:
                break
            page += 1

    run = await session.execute(
        select(IngestRun).where(
            IngestRun.region_code == region_code,
            IngestRun.deal_ym == deal_ym,
            IngestRun.housing_type == housing_type,
            IngestRun.deal_kind == deal_kind,
        )
    )
    ingest_run = run.scalar_one_or_none()
    if ingest_run is None:
        ingest_run = IngestRun(
            region_code=region_code,
            deal_ym=deal_ym,
            housing_type=housing_type,
            deal_kind=deal_kind,
        )
        session.add(ingest_run)
    ingest_run.trade_count = inserted
    ingest_run.status = "ok"
    ingest_run.message = f"inserted={inserted}"
    ingest_run.finished_at = datetime.utcnow()
    await session.commit()
    return inserted


async def ingest_all(
    session: AsyncSession,
    settings: Settings,
    region_codes: list[str] | None = None,
    months: int = 24,
    force: bool = False,
    sources: list[tuple[str, str]] | None = None,
) -> dict:
    await seed_regions(session)
    codes = region_codes or [r["code"] for r in SEOUL_REGIONS]
    deal_months = _month_range(months)
    source_list = sources or DEFAULT_SOURCES
    total_inserted = 0
    errors: list[str] = []
    for code in codes:
        for ym in deal_months:
            for housing_type, deal_kind in source_list:
                try:
                    n = await ingest_region_month(
                        session,
                        settings,
                        code,
                        ym,
                        housing_type,
                        deal_kind,
                        force=force,
                    )
                    total_inserted += n
                    logger.info(
                        "ingested %s %s %s/%s -> %s",
                        code,
                        ym,
                        housing_type,
                        deal_kind,
                        n,
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.exception(
                        "ingest failed %s %s %s/%s", code, ym, housing_type, deal_kind
                    )
                    errors.append(f"{code}/{ym}/{housing_type}/{deal_kind}: {exc}")
                    session.add(
                        IngestRun(
                            region_code=code,
                            deal_ym=ym,
                            housing_type=housing_type,
                            deal_kind=deal_kind,
                            trade_count=0,
                            status="error",
                            message=str(exc)[:500],
                            finished_at=datetime.utcnow(),
                        )
                    )
                    await session.commit()
    return {
        "inserted": total_inserted,
        "regions": len(codes),
        "months": len(deal_months),
        "sources": [f"{h}/{k}" for h, k in source_list],
        "errors": errors,
    }
