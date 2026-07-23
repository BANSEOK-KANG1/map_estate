"""Enrich lots: geocode, POI, market compare, scores."""

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.ingest.molit_market import estimate_market_for_lot
from app.ingest.onbid_detail import enrich_lot_onbid_detail
from app.models import AuctionLot
from app.services.kakao import ensure_lot_coords, get_or_fetch_pois
from app.services.score import apply_lot_scores, infrastructure_score

logger = logging.getLogger(__name__)


async def enrich_lot(
    session: AsyncSession,
    settings: Settings,
    lot: AuctionLot,
    *,
    fetch_market: bool = True,
    fetch_pois: bool = True,
    fetch_detail: bool = True,
) -> AuctionLot:
    if fetch_detail and lot.source == "onbid":
        try:
            await enrich_lot_onbid_detail(session, settings, lot)
        except Exception:  # noqa: BLE001
            logger.exception("onbid detail failed for lot %s", lot.id)

    await ensure_lot_coords(session, settings, lot)

    pois = []
    if fetch_pois:
        try:
            pois = await get_or_fetch_pois(session, settings, lot)
        except Exception:  # noqa: BLE001
            logger.exception("poi fetch failed for lot %s", lot.id)

    if fetch_market:
        try:
            await estimate_market_for_lot(session, settings, lot)
        except Exception:  # noqa: BLE001
            logger.exception("market estimate failed for lot %s", lot.id)

    if pois:
        lot.infra_score = infrastructure_score(pois)
    # infra_score stays None when POI not fetched → excluded from weight
    apply_lot_scores(lot)

    subway = next((p for p in pois if p.category == "subway"), None)
    if subway and subway.payload_json:
        import json

        try:
            places = json.loads(subway.payload_json)
            if places:
                lot.nearest_station = places[0].get("name") or lot.nearest_station
                dist = places[0].get("distance")
                if dist is not None:
                    lot.station_walk_minutes = max(1, int(float(dist) / 80))
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    await session.commit()
    await session.refresh(lot)
    return lot


async def enrich_lots(
    session: AsyncSession,
    settings: Settings,
    lots: list[AuctionLot],
    *,
    fetch_market: bool = True,
    fetch_pois: bool = True,
    fetch_detail: bool = True,
) -> int:
    n = 0
    for lot in lots:
        await enrich_lot(
            session,
            settings,
            lot,
            fetch_market=fetch_market,
            fetch_pois=fetch_pois,
            fetch_detail=fetch_detail,
        )
        n += 1
    return n
