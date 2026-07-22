from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.db import init_db
from app.routers import api, demo

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_WEB_CANDIDATES = [
    _BACKEND_ROOT / "static" / "web",
    _REPO_ROOT / "app" / "build" / "web",
]
WEB_DIR = next((p for p in _WEB_CANDIDATES if p.exists()), _WEB_CANDIDATES[0])

_NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _file_response(path: Path, *, no_cache: bool = False) -> FileResponse:
    headers = dict(_NO_CACHE_HEADERS) if no_cache else None
    return FileResponse(path, headers=headers)


class PrivateNetworkCorsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if (
            request.method == "OPTIONS"
            and request.headers.get("access-control-request-private-network")
        ):
            return Response(
                status_code=204,
                headers={
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "*",
                    "Access-Control-Allow-Headers": request.headers.get(
                        "access-control-request-headers", "*"
                    ),
                    "Access-Control-Allow-Private-Network": "true",
                },
            )
        response = await call_next(request)
        if request.headers.get("access-control-request-private-network"):
            response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    # Free Render has ephemeral disk — refill when waking to an empty DB,
    # and rebalance map coords so 경기/인천 aren't left blank after partial geocode.
    try:
        import asyncio

        from sqlalchemy import func, select

        from app.db import SessionLocal
        from app.models import AuctionLot

        async with SessionLocal() as session:
            total = (await session.execute(select(func.count(AuctionLot.id)))).scalar_one()
        if total == 0:
            asyncio.create_task(_bootstrap_if_empty())
        else:
            asyncio.create_task(_rebalance_geocode_if_needed())
    except Exception:  # noqa: BLE001
        pass
    yield


async def _pick_balanced_ungeocoded(session, per: int = 80) -> list:
    from sqlalchemy import select

    from app.data.regions import GYEONGGI_REGIONS, INCHEON_REGIONS, SEOUL_REGIONS
    from app.models import AuctionLot

    groups = [SEOUL_REGIONS, GYEONGGI_REGIONS, INCHEON_REGIONS]
    targets: list = []
    seen: set[int] = set()
    for group in groups:
        codes = [r["code"] for r in group]
        batch = (
            await session.execute(
                select(AuctionLot)
                .where(
                    AuctionLot.lat.is_(None),
                    AuctionLot.region_code.in_(codes),
                )
                .order_by(
                    AuctionLot.bid_end_at.asc().nullslast(),
                    AuctionLot.id.asc(),
                )
                .limit(per)
            )
        ).scalars().all()
        for lot in batch:
            if lot.id not in seen:
                targets.append(lot)
                seen.add(lot.id)
    return targets


async def _rebalance_geocode_if_needed() -> None:
    """If any MVP sido has lots but almost no map pins, geocode a balanced batch."""
    import logging

    from sqlalchemy import func, select

    from app.data.regions import GYEONGGI_REGIONS, INCHEON_REGIONS, SEOUL_REGIONS
    from app.db import SessionLocal
    from app.models import AuctionLot
    from app.services.enrich import enrich_lots

    logger = logging.getLogger(__name__)
    settings = get_settings()
    if not settings.kakao_rest_key:
        return
    try:
        async with SessionLocal() as session:
            needs = False
            for group in (SEOUL_REGIONS, GYEONGGI_REGIONS, INCHEON_REGIONS):
                codes = [r["code"] for r in group]
                total = (
                    await session.execute(
                        select(func.count(AuctionLot.id)).where(
                            AuctionLot.region_code.in_(codes)
                        )
                    )
                ).scalar_one()
                with_coords = (
                    await session.execute(
                        select(func.count(AuctionLot.id)).where(
                            AuctionLot.region_code.in_(codes),
                            AuctionLot.lat.isnot(None),
                        )
                    )
                ).scalar_one()
                if total >= 20 and with_coords < 10:
                    needs = True
                    break
            if not needs:
                return
            targets = await _pick_balanced_ungeocoded(session, per=70)
            if not targets:
                return
            n = await enrich_lots(
                session,
                settings,
                targets,
                fetch_market=False,
                fetch_pois=False,
                fetch_detail=False,
            )
            logger.info("rebalance geocode: %s lots", n)
    except Exception:  # noqa: BLE001
        logger.exception("rebalance geocode failed")


async def _bootstrap_if_empty() -> None:
    """Background: onbid ingest + light geocode when DB starts empty."""
    import logging

    from sqlalchemy import func, select

    from app.db import SessionLocal
    from app.ingest.onbid import ingest_onbid
    from app.models import AuctionLot
    from app.services.enrich import enrich_lots
    from app.services.lots import seed_regions

    logger = logging.getLogger(__name__)
    settings = get_settings()
    if not settings.onbid_service_key:
        logger.warning("bootstrap skipped: ONBID_SERVICE_KEY missing")
        return
    try:
        async with SessionLocal() as session:
            total = (await session.execute(select(func.count(AuctionLot.id)))).scalar_one()
            if total > 0:
                return
            await seed_regions(session)
            run = await ingest_onbid(session, settings, max_pages=10, page_size=100)
            logger.info("bootstrap ingest: %s lots (%s)", run.lot_count, run.message[:120])
            if settings.kakao_rest_key and run.lot_count > 0:
                targets = await _pick_balanced_ungeocoded(session, per=80)
                if targets:
                    n = await enrich_lots(
                        session,
                        settings,
                        targets,
                        fetch_market=False,
                        fetch_pois=False,
                        fetch_detail=False,
                    )
                    logger.info("bootstrap geocode: %s lots", n)
    except Exception:  # noqa: BLE001
        logger.exception("bootstrap failed")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Auction Insight API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(PrivateNetworkCorsMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api.router, prefix="/api")
    app.include_router(demo.router, prefix="/api")

    if WEB_DIR.exists():
        assets = WEB_DIR / "assets"
        if assets.exists():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.get("/")
        async def spa_index():
            return _file_response(WEB_DIR / "index.html", no_cache=True)

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            candidate = WEB_DIR / full_path
            if candidate.is_file():
                no_cache = candidate.suffix in {".html", ".js", ".json"} or candidate.name in {
                    "flutter_bootstrap.js",
                    "main.dart.js",
                    "flutter.js",
                    "version.json",
                }
                return _file_response(candidate, no_cache=no_cache)
            index = WEB_DIR / "index.html"
            if index.exists() and not full_path.startswith("api"):
                return _file_response(index, no_cache=True)
            return Response(status_code=404)

    return app


app = create_app()
