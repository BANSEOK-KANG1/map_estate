"""Kakao Local helpers for geocoding and POI."""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AuctionLot, PoiCache

logger = logging.getLogger(__name__)

KAKAO_LOCAL = "https://dapi.kakao.com/v2/local"

POI_CATEGORIES: dict[str, tuple[str, str]] = {
    "SW8": ("subway", "지하철"),
    "SC4": ("school", "학교"),
    "HP8": ("hospital", "병원"),
    "MT1": ("mart", "대형마트"),
    "CS2": ("convenience", "편의점"),
    "CE7": ("cafe", "카페"),
    "FD6": ("food", "음식점"),
}

POI_CACHE_TTL = timedelta(days=7)


def _headers(settings: Settings) -> dict[str, str]:
    return {"Authorization": f"KakaoAK {settings.kakao_rest_key}"}


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _geocode_query_variants(address: str) -> list[str]:
    """Strip floor/unit/usage noise so Kakao can match a street address."""
    import re

    raw = " ".join(address.split()).strip()
    if not raw:
        return []
    variants: list[str] = [raw]
    cleaned = re.sub(r"\s*제?\d+\s*층\b.*$", "", raw)
    cleaned = re.sub(r"\s*제?\d+\s*호\b.*$", "", cleaned)
    cleaned = re.sub(
        r"\s+(오피스텔|아파트|다세대주택|다세대|다가구|근린생활시설|업무시설|단독주택|연립주택)\b.*$",
        "",
        cleaned,
    )
    cleaned = cleaned.strip(" ,")
    if cleaned and cleaned not in variants:
        variants.append(cleaned)
    # Keep "시/군/구 … 동 … 번지" head when title is long
    m = re.match(
        r"^((?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)"
        r"[^\d]{0,40}?\d[\d\-]*)",
        cleaned or raw,
    )
    if m:
        short = m.group(1).strip()
        if short and short not in variants:
            variants.append(short)
    return variants


async def geocode_address(
    settings: Settings,
    address: str,
) -> tuple[float, float] | None:
    if not settings.kakao_rest_key or not address.strip():
        return None
    async with httpx.AsyncClient() as client:
        for query in _geocode_query_variants(address):
            resp = await client.get(
                f"{KAKAO_LOCAL}/search/address.json",
                params={"query": query},
                headers=_headers(settings),
                timeout=20.0,
            )
            if resp.status_code != 200:
                logger.warning("geocode failed: %s %s", resp.status_code, resp.text[:200])
                continue
            docs = resp.json().get("documents") or []
            if not docs:
                resp2 = await client.get(
                    f"{KAKAO_LOCAL}/search/keyword.json",
                    params={"query": query},
                    headers=_headers(settings),
                    timeout=20.0,
                )
                docs = resp2.json().get("documents") or []
            if docs:
                return float(docs[0]["y"]), float(docs[0]["x"])
        return None


async def ensure_lot_coords(
    session: AsyncSession,
    settings: Settings,
    lot: AuctionLot,
) -> AuctionLot:
    if lot.lat is not None and lot.lng is not None:
        return lot
    coords = await geocode_address(settings, lot.address)
    if coords:
        lot.lat, lot.lng = coords
        lot.geocoded_at = datetime.utcnow()
        await session.commit()
        await session.refresh(lot)
    return lot


async def search_category(
    settings: Settings,
    lat: float,
    lng: float,
    category_code: str,
    radius: int = 800,
) -> list[dict]:
    if not settings.kakao_rest_key:
        return []
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{KAKAO_LOCAL}/search/category.json",
            params={
                "category_group_code": category_code,
                "x": str(lng),
                "y": str(lat),
                "radius": radius,
                "sort": "distance",
                "size": 15,
            },
            headers=_headers(settings),
            timeout=20.0,
        )
        if resp.status_code != 200:
            logger.warning("category search failed: %s", resp.status_code)
            return []
        return resp.json().get("documents") or []


async def get_or_fetch_pois(
    session: AsyncSession,
    settings: Settings,
    lot: AuctionLot,
    radius: int = 800,
) -> list[PoiCache]:
    if lot.lat is None or lot.lng is None:
        return []
    results: list[PoiCache] = []
    now = datetime.utcnow()
    for code, (key, _label) in POI_CATEGORIES.items():
        cached = await session.execute(
            select(PoiCache).where(PoiCache.lot_id == lot.id, PoiCache.category == key)
        )
        row = cached.scalar_one_or_none()
        if row and now - row.fetched_at < POI_CACHE_TTL:
            results.append(row)
            continue
        docs = await search_category(settings, lot.lat, lot.lng, code, radius)
        nearest = float(docs[0]["distance"]) if docs else None
        payload = json.dumps(
            [{"name": d.get("place_name"), "distance": d.get("distance")} for d in docs[:5]],
            ensure_ascii=False,
        )
        if row is None:
            row = PoiCache(lot_id=lot.id, category=key)
            session.add(row)
        row.count = len(docs)
        row.nearest_distance_m = nearest
        row.payload_json = payload
        row.fetched_at = now
        results.append(row)
    await session.commit()
    return results
