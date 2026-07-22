from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()

# Ensure SQLite data directory exists
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.split("///")[-1]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.database_url, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def _sqlite_add_columns(connection) -> None:
    """Best-effort ALTER for existing SQLite DBs (create_all won't add columns)."""
    from sqlalchemy import text

    if not settings.database_url.startswith("sqlite"):
        return
    rows = connection.execute(text("PRAGMA table_info(auction_lots)")).fetchall()
    cols = {r[1] for r in rows}
    alters = []
    if "pbct_cdtn_no" not in cols:
        alters.append("ALTER TABLE auction_lots ADD COLUMN pbct_cdtn_no VARCHAR(32) DEFAULT ''")
    if "detail_json" not in cols:
        alters.append("ALTER TABLE auction_lots ADD COLUMN detail_json TEXT DEFAULT '{}'")
    for stmt in alters:
        connection.execute(text(stmt))


async def init_db() -> None:
    from app import models  # noqa: F401
    from app.analysis import models as analysis_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sqlite_add_columns)
