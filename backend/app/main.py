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

# repo_root/app/build/web (local) or backend/static/web (deploy)
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[2]
_WEB_CANDIDATES = [
    _BACKEND_ROOT / "static" / "web",
    _REPO_ROOT / "app" / "build" / "web",
]
WEB_DIR = next((p for p in _WEB_CANDIDATES if p.exists()), _WEB_CANDIDATES[0])


class PrivateNetworkCorsMiddleware(BaseHTTPMiddleware):
    """Chrome Private Network Access: allow localhost page → local API."""

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
        response.headers["Access-Control-Allow-Private-Network"] = "true"
        return response


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.database_url.startswith("sqlite"):
        raw = settings.database_url.split("///")[-1]
        Path(raw).parent.mkdir(parents=True, exist_ok=True)
    await init_db()
    # Render free disk is ephemeral — bootstrap demo when empty and no MOLIT key.
    if not settings.molit_service_key.strip():
        from sqlalchemy import func, select

        from app.db import SessionLocal
        from app.models import Complex
        from app.routers.demo import run_demo_seed

        async with SessionLocal() as db:
            count = await db.scalar(select(func.count()).select_from(Complex))
            if not count:
                await run_demo_seed(db, count=160)
    yield


app = FastAPI(
    title="Map Estate API",
    description="원룸·다가구 실거래·상권·출퇴근 API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(PrivateNetworkCorsMiddleware)

app.include_router(api.router, prefix="/api")
app.include_router(demo.router, prefix="/api")


@app.get("/api/meta")
async def meta():
    return {
        "name": "map-estate",
        "docs": "/docs",
        "web": "/" if WEB_DIR.exists() else None,
    }


def _mount_web() -> None:
    if not WEB_DIR.exists():
        @app.get("/")
        async def root_fallback():
            return {
                "name": "map-estate",
                "docs": "/docs",
                "hint": "Flutter web build missing. Run: cd app && flutter build web",
            }
        return

    assets = WEB_DIR / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/")
    async def index():
        return FileResponse(WEB_DIR / "index.html")

    @app.get("/{full_path:path}")
    async def spa(full_path: str):
        # Keep API/docs/openapi untouched (already registered).
        if full_path.startswith(("api", "docs", "openapi", "redoc")):
            return Response(status_code=404)
        candidate = WEB_DIR / full_path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(WEB_DIR / "index.html")


_mount_web()
