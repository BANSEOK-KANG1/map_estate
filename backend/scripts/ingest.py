#!/usr/bin/env python3
"""CLI ingest: python -m scripts.ingest --months 6 --regions 11680 --sources officetel:rent villa:rent"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.db import SessionLocal, init_db
from app.ingest.molit_small_housing import ingest_all


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--months", type=int, default=6)
    parser.add_argument("--regions", nargs="*", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--sources",
        nargs="*",
        default=None,
        help="e.g. officetel:rent villa:rent multi:sale",
    )
    args = parser.parse_args()

    sources = None
    if args.sources:
        sources = []
        for s in args.sources:
            h, k = s.split(":")
            sources.append((h, k))

    await init_db()
    settings = get_settings()
    async with SessionLocal() as session:
        result = await ingest_all(
            session,
            settings,
            region_codes=args.regions,
            months=args.months,
            force=args.force,
            sources=sources,
        )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
