"""Auction analysis lab — additive module for beginner-safe court/onbid review."""

__all__ = ["router"]


def __getattr__(name: str):
    if name == "router":
        from app.analysis.router import router

        return router
    raise AttributeError(name)
