"""Optional API key gate for analysis write endpoints."""

from __future__ import annotations

import os


def analysis_api_key() -> str:
    return (os.getenv("ANALYSIS_API_KEY") or "").strip()


def is_analysis_write(method: str, path: str) -> bool:
    """True when this analysis route should require X-API-Key (if configured)."""
    if not path.startswith("/api/analysis"):
        return False
    if method.upper() in {"GET", "HEAD", "OPTIONS"}:
        return False
    # money validate is calculator UX — allow without key
    if path.rstrip("/").endswith("/money/validate"):
        return False
    return True


def build_analysis_api_key_middleware():
    """Lazy import Starlette so unit tests can import helpers without ASGI deps."""
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.requests import Request
    from starlette.responses import Response

    class AnalysisApiKeyMiddleware(BaseHTTPMiddleware):
        """When ANALYSIS_API_KEY is set, require X-API-Key on analysis mutating routes."""

        async def dispatch(self, request: Request, call_next):
            expected = analysis_api_key()
            if expected and is_analysis_write(request.method, request.url.path):
                got = (request.headers.get("X-API-Key") or "").strip()
                if got != expected:
                    return Response(
                        content='{"detail":"invalid or missing X-API-Key"}',
                        status_code=401,
                        media_type="application/json",
                    )
            return await call_next(request)

    return AnalysisApiKeyMiddleware
