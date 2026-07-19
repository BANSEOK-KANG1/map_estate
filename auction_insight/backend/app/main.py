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
    # Free Render has ephemeral disk — refill when waking to an empty DB.
    try:
        import asyncio

        from sqlalchemy import func, select

        from app.db import SessionLocal
        from app.models import AuctionLot

        async with SessionLocal() as session:
            total = (await session.execute(select(func.count(AuctionLot.id)))).scalar_one()
        if total == 0:
            asyncio.create_task(_bootstrap_if_empty())
    except Exception:  # noqa: BLE001
        pass
    yield


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
                lots = (
                    await session.execute(
                        select(AuctionLot)
                        .where(AuctionLot.lat.is_(None))
                        .order_by(AuctionLot.bid_end_at.asc().nullslast())
                        .limit(120)
                    )
                ).scalars().all()
                if lots:
                    n = await enrich_lots(
                        session,
                        settings,
                        list(lots),
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
            return FileResponse(WEB_DIR / "index.html")

        @app.get("/{full_path:path}")
        async def spa_fallback(full_path: str):
            candidate = WEB_DIR / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            index = WEB_DIR / "index.html"
            if index.exists() and not full_path.startswith("api"):
                return FileResponse(index)
            return Response(status_code=404)

    return app


app = create_app()
