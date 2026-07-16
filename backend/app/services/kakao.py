"""Kakao Local / Directions REST helpers."""

from __future__ import annotations

import json
import logging
import math
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import Complex, PoiCache

logger = logging.getLogger(__name__)

KAKAO_LOCAL = "https://dapi.kakao.com/v2/local"
KAKAO_MOBILITY = "https://apis-navi.kakaomobility.com/v1"

# category_group_code → (internal key, Korean label)
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


async def geocode_address(
    settings: Settings,
    address: str,
) -> tuple[float, float] | None:
    if not settings.kakao_rest_key:
        return None
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{KAKAO_LOCAL}/search/address.json",
            params={"query": address},
            headers=_headers(settings),
            timeout=20.0,
        )
        if resp.status_code != 200:
            logger.warning("geocode failed: %s %s", resp.status_code, resp.text[:200])
            return None
        docs = resp.json().get("documents") or []
        if not docs:
            # fallback keyword search
            resp2 = await client.get(
                f"{KAKAO_LOCAL}/search/keyword.json",
                params={"query": address},
                headers=_headers(settings),
                timeout=20.0,
            )
            docs = resp2.json().get("documents") or []
        if not docs:
            return None
        return float(docs[0]["y"]), float(docs[0]["x"])


async def ensure_complex_coords(
    session: AsyncSession,
    settings: Settings,
    complex_: Complex,
) -> Complex:
    if complex_.lat is not None and complex_.lng is not None:
        return complex_
    address = f"서울 {complex_.dong} {complex_.jibun}".strip()
    if complex_.road_name:
        address = f"서울 {complex_.road_name}"
    coords = await geocode_address(settings, f"{complex_.name} {address}")
    if coords is None:
        coords = await geocode_address(settings, address)
    if coords:
        complex_.lat, complex_.lng = coords
        complex_.geocoded_at = datetime.utcnow()
        await session.commit()
        await session.refresh(complex_)
    return complex_


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
    complex_: Complex,
    radius: int = 800,
) -> list[PoiCache]:
    if complex_.lat is None or complex_.lng is None:
        return []
    results: list[PoiCache] = []
    now = datetime.utcnow()
    for code, (key, _label) in POI_CATEGORIES.items():
        cached = await session.execute(
            select(PoiCache).where(
                PoiCache.complex_id == complex_.id,
                PoiCache.category == key,
            )
        )
        row = cached.scalar_one_or_none()
        if row and now - row.fetched_at < POI_CACHE_TTL:
            results.append(row)
            continue
        docs = await search_category(settings, complex_.lat, complex_.lng, code, radius)
        nearest = float(docs[0]["distance"]) if docs else None
        payload = json.dumps(
            [{"name": d.get("place_name"), "distance": d.get("distance")} for d in docs[:5]],
            ensure_ascii=False,
        )
        if row is None:
            row = PoiCache(complex_id=complex_.id, category=key)
            session.add(row)
        row.count = len(docs)
        row.nearest_distance_m = nearest
        row.payload_json = payload
        row.fetched_at = now
        results.append(row)
    await session.commit()
    return results


async def driving_duration_minutes(
    settings: Settings,
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> tuple[float | None, float | None, str]:
    """Return (minutes, meters, source). Prefer Kakao Mobility; fallback to haversine heuristic."""
    if settings.kakao_rest_key:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{KAKAO_MOBILITY}/directions",
                    params={
                        "origin": f"{origin_lng},{origin_lat}",
                        "destination": f"{dest_lng},{dest_lat}",
                    },
                    headers=_headers(settings),
                    timeout=20.0,
                )
                if resp.status_code == 200:
                    routes = resp.json().get("routes") or []
                    if routes:
                        summary = routes[0].get("summary") or {}
                        duration_s = summary.get("duration")
                        distance = summary.get("distance")
                        if duration_s is not None:
                            return float(duration_s) / 60.0, float(distance or 0), "kakao_driving"
        except Exception:  # noqa: BLE001
            logger.exception("directions failed")

    dist = haversine_m(origin_lat, origin_lng, dest_lat, dest_lng)
    # ~25 km/h urban average for rough ETA
    minutes = (dist / 1000.0) / 25.0 * 60.0
    return minutes, dist, "haversine_heuristic"
