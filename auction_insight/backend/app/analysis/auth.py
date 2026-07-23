"""Optional API key gate for analysis write endpoints."""

from __future__ import annotations

import os

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


def analysis_api_key() -> str:
    return (os.getenv("ANALYSIS_API_KEY") or "").strip()


def _is_analysis_write(request: Request) -> bool:
    path = request.url.path
    if not path.startswith("/api/analysis"):
        return False
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return False
    # money validate is calculator UX — allow without key
    if path.rstrip("/").endswith("/money/validate"):
        return False
    return True


class AnalysisApiKeyMiddleware(BaseHTTPMiddleware):
    """When ANALYSIS_API_KEY is set, require X-API-Key on analysis mutating routes."""

    async def dispatch(self, request: Request, call_next):
        expected = analysis_api_key()
        if expected and _is_analysis_write(request):
            got = (request.headers.get("X-API-Key") or "").strip()
            if got != expected:
                return Response(
                    content='{"detail":"invalid or missing X-API-Key"}',
                    status_code=401,
                    media_type="application/json",
                )
        return await call_next(request)
