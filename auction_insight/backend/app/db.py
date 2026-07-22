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

    # analysis documents (Phase 2)
    try:
        drows = connection.execute(
            text("PRAGMA table_info(analysis_auction_documents)")
        ).fetchall()
    except Exception:  # noqa: BLE001
        return
    if not drows:
        return
    dcols = {r[1] for r in drows}
    dalters = []
    if "pages_json" not in dcols:
        dalters.append(
            "ALTER TABLE analysis_auction_documents ADD COLUMN pages_json TEXT DEFAULT '[]'"
        )
    if "classify_confidence" not in dcols:
        dalters.append(
            "ALTER TABLE analysis_auction_documents ADD COLUMN classify_confidence FLOAT DEFAULT 0"
        )
    if "classify_note" not in dcols:
        dalters.append(
            "ALTER TABLE analysis_auction_documents ADD COLUMN classify_note VARCHAR(256) DEFAULT ''"
        )
    for stmt in dalters:
        connection.execute(text(stmt))

    # analysis rights (Phase 3)
    try:
        rrows = connection.execute(
            text("PRAGMA table_info(analysis_right_entries)")
        ).fetchall()
    except Exception:  # noqa: BLE001
        return
    if not rrows:
        return
    rcols = {r[1] for r in rrows}
    ralters = []
    if "event_date" not in rcols:
        ralters.append("ALTER TABLE analysis_right_entries ADD COLUMN event_date DATE")
    if "is_malso_baseline" not in rcols:
        ralters.append(
            "ALTER TABLE analysis_right_entries ADD COLUMN is_malso_baseline INTEGER DEFAULT 0"
        )
    for stmt in ralters:
        connection.execute(text(stmt))


async def init_db() -> None:
    from app import models  # noqa: F401
    from app.analysis import models as analysis_models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_sqlite_add_columns)
