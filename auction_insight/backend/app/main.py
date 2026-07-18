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
    yield


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
