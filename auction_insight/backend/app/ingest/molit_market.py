"""국토부 실거래로 인근 시세 추정."""

from __future__ import annotations

import logging
import statistics
from datetime import date
from xml.etree.ElementTree import Element

import httpx
from defusedxml import ElementTree as ET
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AuctionLot, NearbyTrade

logger = logging.getLogger(__name__)

APT_TRADE = "https://apis.data.go.kr/1613000/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade"
OFFI_TRADE = "https://apis.data.go.kr/1613000/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade"
RH_TRADE = "https://apis.data.go.kr/1613000/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade"


def _text(el: Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text.strip()


def _parse_price(raw: str) -> int:
    return int(raw.replace(",", "").replace(" ", "") or "0")


def _month_list(n: int = 4) -> list[str]:
    today = date.today()
    y, m = today.year, today.month
    m -= 1
    if m == 0:
        m = 12
        y -= 1
    out: list[str] = []
    for _ in range(n):
        out.append(f"{y:04d}{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return out


def _endpoint_candidates(usage: str) -> list[tuple[str, str, str]]:
    """(endpoint, housing_type, label) — preferred first, then fallbacks."""
    u = (usage or "").lower()
    if "오피스" in usage or "officetel" in u:
        order = [
            (OFFI_TRADE, "officetel", "오피스텔 매매"),
            (RH_TRADE, "villa", "연립다세대 매매"),
            (APT_TRADE, "apt", "아파트 매매"),
        ]
    elif "다가구" in usage or "다세대" in usage or "연립" in usage or "빌라" in usage:
        order = [
            (RH_TRADE, "villa", "연립다세대 매매"),
            (OFFI_TRADE, "officetel", "오피스텔 매매"),
            (APT_TRADE, "apt", "아파트 매매"),
        ]
    else:
        order = [
            (APT_TRADE, "apt", "아파트 매매"),
            (OFFI_TRADE, "officetel", "오피스텔 매매"),
            (RH_TRADE, "villa", "연립다세대 매매"),
        ]
    return order


async def fetch_region_trades(
    settings: Settings,
    region_code: str,
    deal_ym: str,
    endpoint: str,
) -> tuple[list[dict], str | None]:
    """Return (items, error). error is 'forbidden' | 'http' | 'parse' | None."""
    if not settings.molit_service_key:
        return [], "no_key"
    params = {
        "serviceKey": settings.molit_service_key,
        "LAWD_CD": region_code,
        "DEAL_YMD": deal_ym,
        "numOfRows": 100,
        "pageNo": 1,
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(endpoint, params=params, timeout=30.0)
    except httpx.HTTPError as exc:
        logger.warning("molit network error: %s", exc)
        return [], "network"

    if resp.status_code == 403:
        return [], "forbidden"
    if resp.status_code != 200:
        logger.warning("molit HTTP %s %s", resp.status_code, endpoint.split("/")[-1])
        return [], "http"

    text = resp.text
    if "SERVICE ERROR" in text.upper() or "FORBIDDEN" in text.upper():
        return [], "forbidden"
    if "<resultCode>99" in text or "인증" in text and "오류" in text:
        return [], "forbidden"

    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return [], "parse"

    items = []
    for item in root.findall(".//item"):
        area = _text(item.find("excluUseAr")) or _text(item.find("전용면적"))
        price = _text(item.find("dealAmount")) or _text(item.find("거래금액"))
        dong = _text(item.find("umdNm")) or _text(item.find("법정동"))
        apt = (
            _text(item.find("aptNm"))
            or _text(item.find("단지"))
            or _text(item.find("offiNm"))
            or _text(item.find("mhouseNm"))
        )
        year = _text(item.find("dealYear")) or _text(item.find("년"))
        month = _text(item.find("dealMonth")) or _text(item.find("월"))
        day = _text(item.find("dealDay")) or _text(item.find("일"))
        if not area or not price:
            continue
        try:
            exclusive = float(area)
            price_m = _parse_price(price)
        except ValueError:
            continue
        deal_date = None
        try:
            if year and month and day:
                deal_date = date(int(year), int(month), int(day))
        except ValueError:
            pass
        items.append(
            {
                "dong": dong.strip(),
                "name": apt,
                "exclusive_area": exclusive,
                "price_manwon": price_m,
                "deal_date": deal_date,
                "deal_ym": deal_ym,
            }
        )
    return items, None


def _area_compatible(lot_area: float | None, trade_area: float, tol: float = 0.30) -> bool:
    if lot_area is None or lot_area <= 0:
        return True
    return abs(trade_area - lot_area) / lot_area <= tol


async def estimate_market_for_lot(
    session: AsyncSession,
    settings: Settings,
    lot: AuctionLot,
) -> dict:
    """Fill market_* fields from Molit (fallback across housing types)."""
    await session.execute(delete(NearbyTrade).where(NearbyTrade.lot_id == lot.id))

    if not lot.region_code or not settings.molit_service_key:
        if not lot.market_note:
            lot.market_note = "시세 API 키 또는 지역코드 없음"
        return {"sample_count": 0, "note": "no_region_or_key"}

    samples: list[dict] = []
    used_label = ""
    used_housing = "apt"
    months = _month_list(4)
    last_err = None

    for endpoint, housing, label in _endpoint_candidates(lot.usage):
        collected: list[dict] = []
        forbidden = False
        for ym in months:
            rows, err = await fetch_region_trades(settings, lot.region_code, ym, endpoint)
            if err == "forbidden":
                forbidden = True
                last_err = err
                break
            if err:
                last_err = err
                continue
            for r in rows:
                if _area_compatible(lot.exclusive_area, r["exclusive_area"]):
                    collected.append(r)
        if forbidden:
            continue
        if len(collected) < 3:
            # relax area filter
            collected = []
            for ym in months:
                rows, err = await fetch_region_trades(settings, lot.region_code, ym, endpoint)
                if err == "forbidden":
                    forbidden = True
                    break
                if not err:
                    collected.extend(rows)
            if forbidden:
                continue
        if collected:
            samples = collected
            used_label = label
            used_housing = housing
            break

    for r in samples[:40]:
        session.add(
            NearbyTrade(
                lot_id=lot.id,
                region_code=lot.region_code or "",
                deal_ym=r["deal_ym"],
                housing_type=used_housing,
                address=f"{r['dong']} {r['name']}".strip(),
                exclusive_area=r["exclusive_area"],
                price_manwon=r["price_manwon"],
                deal_date=r["deal_date"],
                distance_m=None,
            )
        )

    if not samples:
        note = "국토부 실거래 조회 실패 또는 미승인 API"
        if last_err == "forbidden":
            note = "해당 유형 실거래 API 미승인(403). 오피스텔 등 승인된 API만 사용 가능"
        lot.market_median_manwon = lot.market_median_manwon  # keep demo if any
        if lot.market_sample_count == 0:
            lot.market_median_manwon = None
            lot.market_pyeong_manwon = None
        lot.market_note = note
        return {"sample_count": 0, "note": note}

    prices = [s["price_manwon"] for s in samples]
    median = int(statistics.median(prices))
    pyeong_prices = []
    for s in samples:
        if s["exclusive_area"] > 0:
            pyeong = s["exclusive_area"] / 3.3058
            if pyeong > 0:
                pyeong_prices.append(s["price_manwon"] / pyeong)

    lot.market_median_manwon = median
    lot.market_sample_count = len(samples)
    lot.market_pyeong_manwon = round(statistics.median(pyeong_prices), 1) if pyeong_prices else None
    dong = lot.dong or "인근"
    lot.market_note = (
        f"{dong} {used_label} 중위가 (최근 {len(months)}개월·표본 {len(samples)}건, 국토부 실거래)"
    )
    return {"sample_count": len(samples), "median": median, "source": used_label}
