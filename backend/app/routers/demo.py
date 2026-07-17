"""원룸·오피스텔·빌라·다가구 — 대량 데모 시드 (역세권 기반)."""

from __future__ import annotations

import json
from datetime import date
from math import cos, radians
from random import Random

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.seoul_regions import SEOUL_REGIONS
from app.data.subway_stations import SEOUL_STATIONS
from app.db import Base, engine, get_db
from app.ingest.molit_small_housing import seed_regions
from app.models import Complex, Trade

router = APIRouter(prefix="/demo", tags=["demo"])

REGION_NAME = {r["code"]: r["name"] for r in SEOUL_REGIONS}

NAME_PREFIX = [
    "시티",
    "포레",
    "하임",
    "스테이",
    "하우스",
    "빌",
    "레지던스",
    "루체",
    "애비뉴",
    "골든",
    "프라임",
    "센트럴",
    "더샵",
    "아이파크",
    "블루",
]
NAME_SUFFIX = ["원룸", "오피스텔", "빌리지", "하우스", "코리빙", "스튜디오", "룸"]


def _offset_coords(lat: float, lng: float, meters_n: float, meters_e: float) -> tuple[float, float]:
    dlat = meters_n / 111_320
    dlng = meters_e / (111_320 * cos(radians(lat)))
    return lat + dlat, lng + dlng


def _months_back(n: int) -> list[tuple[int, int]]:
    y, m = 2026, 5
    out: list[tuple[int, int]] = []
    for _ in range(n):
        out.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def generate_listings(count: int = 160, seed: int = 42) -> list[dict]:
    rng = Random(seed)
    listings: list[dict] = []
    for i in range(count):
        st = SEOUL_STATIONS[i % len(SEOUL_STATIONS)]
        region_code = st["region_code"]
        housing_roll = rng.random()
        if housing_roll < 0.45:
            housing_type = "officetel"
        elif housing_roll < 0.85:
            housing_type = "villa"
        else:
            housing_type = "multi"

        # Price bands by station premium (rough)
        premium = {
            "강남",
            "역삼",
            "선릉",
            "삼성",
            "신논현",
            "압구정로데오",
            "여의도",
            "성수",
            "잠실",
        }
        mid = {"홍대입구", "합정", "신촌", "건대입구", "왕십리", "문정", "당산"}
        if st["name"] in premium:
            base_deposit = rng.choice([1000, 2000, 3000, 5000, 10000])
            base_monthly = rng.randint(55, 120)
            sale_base = rng.randint(18000, 45000)
        elif st["name"] in mid:
            base_deposit = rng.choice([500, 1000, 2000, 3000])
            base_monthly = rng.randint(40, 85)
            sale_base = rng.randint(12000, 28000)
        else:
            base_deposit = rng.choice([300, 500, 1000, 2000])
            base_monthly = rng.randint(28, 65)
            sale_base = rng.randint(8000, 20000)

        deal_kind = "sale" if housing_type == "multi" and rng.random() < 0.55 else "rent"
        if housing_type == "multi" and deal_kind == "sale":
            areas = sorted([round(rng.uniform(42, 78), 1), round(rng.uniform(50, 95), 1)])
        elif housing_type == "officetel":
            areas = sorted([round(rng.uniform(16, 28), 1), round(rng.uniform(22, 36), 1)])
        else:
            areas = sorted([round(rng.uniform(14, 24), 1), round(rng.uniform(18, 32), 1)])

        north = rng.uniform(-450, 450)
        east = rng.uniform(-450, 450)
        lat, lng = _offset_coords(st["lat"], st["lng"], north, east)
        walk_m = (north**2 + east**2) ** 0.5
        walk_min = max(1, int(walk_m / 80))  # ~80m/min

        gubun = REGION_NAME.get(region_code, "")
        name = (
            f"{st['name']}{rng.choice(NAME_PREFIX)}"
            f"{rng.choice(NAME_SUFFIX)}"
            f"{rng.randint(1, 99)}"
        )
        build_year = rng.randint(1995, 2024)
        floor_max = rng.randint(3, 18) if housing_type == "officetel" else rng.randint(2, 6)
        facing = rng.choice(["남향", "남동향", "남서향", "동향", "서향", "북향", "북동향"])
        move_in_ok = housing_type != "officetel" or rng.random() > 0.25
        # 융자: 매매는 시세의 일부, 월세는 0~소액
        if deal_kind == "sale":
            loan = int(sale_base * rng.uniform(0.0, 0.45))
        else:
            loan = rng.choice([0, 0, 0, 500, 1000, 2000])
        room_count = 1 if min(areas) < 30 else rng.choice([1, 1, 2])
        bath_count = 1 if room_count == 1 else rng.choice([1, 2])
        parking = housing_type == "officetel" or rng.random() > 0.4
        agent_n = rng.randint(1, 40)
        photos = [
            f"https://picsum.photos/seed/{i}a{rng.randint(1,9999)}/960/640",
            f"https://picsum.photos/seed/{i}b{rng.randint(1,9999)}/960/640",
            f"https://picsum.photos/seed/{i}c{rng.randint(1,9999)}/960/640",
            f"https://picsum.photos/seed/{i}d{rng.randint(1,9999)}/960/640",
        ]
        desc = (
            f"{st['name']}역 도보 {walk_min}분. {facing}. "
            f"{'전입신고 가능' if move_in_ok else '전입신고 제한(문의)'} · "
            f"{'주차 가능' if parking else '주차 협의'} · "
            f"{room_count}룸 {bath_count}욕실. "
            f"{'신축급 인테리어' if build_year >= 2018 else '관리상태 양호'}."
        )

        listings.append(
            {
                "region_code": region_code,
                "name": name,
                "housing_type": housing_type,
                "dong": f"{st['name']}동" if not st["name"].endswith("동") else st["name"],
                "jibun": f"{rng.randint(1, 999)}-{rng.randint(1, 40)}",
                "road_name": f"서울특별시 {gubun} {st['name']}로 {rng.randint(10, 200)}",
                "build_year": build_year,
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "deal_kind": deal_kind,
                "base_deposit": base_deposit if deal_kind == "rent" else sale_base,
                "base_monthly": base_monthly if deal_kind == "rent" else 0,
                "areas": areas,
                "station_name": st["name"],
                "station_line": st["line"],
                "walk_minutes": walk_min,
                "floor_max": floor_max,
                "tags": _tags(housing_type, build_year, walk_min, deal_kind, base_deposit, base_monthly),
                "facing": facing,
                "move_in_ok": move_in_ok,
                "loan_manwon": loan,
                "room_count": room_count,
                "bath_count": bath_count,
                "parking": parking,
                "agent_name": f"김중개{agent_n:02d}",
                "agent_phone": f"010-{rng.randint(1000,9999)}-{rng.randint(1000,9999)}",
                "agent_office": f"{st['name']}공인중개사사무소",
                "photo_urls": photos,
                "description": desc,
                "listed_at": date(2026, 5, rng.randint(1, 28)),
            }
        )
    return listings


def _tags(
    housing_type: str,
    build_year: int,
    walk_min: int,
    deal_kind: str,
    deposit: int,
    monthly: int,
) -> list[str]:
    tags: list[str] = []
    if walk_min <= 5:
        tags.append("역세권5분")
    elif walk_min <= 10:
        tags.append("도보10분")
    if build_year >= 2018:
        tags.append("신축급")
    elif build_year >= 2010:
        tags.append("준신축")
    if housing_type == "officetel":
        tags.append("오피스텔")
    elif housing_type == "villa":
        tags.append("빌라원룸")
    else:
        tags.append("다가구")
    if deal_kind == "rent":
        if deposit <= 500:
            tags.append("저보증")
        if monthly <= 50:
            tags.append("월세추천")
        if deposit >= 5000 and monthly <= 30:
            tags.append("반전세형")
    else:
        tags.append("매매")
    return tags[:4]


@router.get("/stations")
async def list_stations():
    return [
        {
            "name": s["name"],
            "line": s["line"],
            "lat": s["lat"],
            "lng": s["lng"],
            "region_code": s["region_code"],
            "region_name": REGION_NAME.get(s["region_code"], ""),
        }
        for s in SEOUL_STATIONS
    ]


async def run_demo_seed(db: AsyncSession, count: int = 160) -> dict:
    """Reset DB and load demo listings. Used by HTTP + startup bootstrap."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await seed_regions(db)

    rng = Random(42)
    months = _months_back(18)
    listings = generate_listings(count=count)
    created_complexes = 0
    created_trades = 0

    for spec in listings:
        complex_ = Complex(
            region_code=spec["region_code"],
            name=spec["name"],
            housing_type=spec["housing_type"],
            dong=spec["dong"],
            jibun=spec["jibun"],
            road_name=spec["road_name"],
            build_year=spec["build_year"],
            lat=spec["lat"],
            lng=spec["lng"],
            facing=spec["facing"],
            move_in_ok=spec["move_in_ok"],
            loan_manwon=spec["loan_manwon"],
            room_count=spec["room_count"],
            bath_count=spec["bath_count"],
            parking=spec["parking"],
            agent_name=spec["agent_name"],
            agent_phone=spec["agent_phone"],
            agent_office=spec["agent_office"],
            photo_urls=json.dumps(spec["photo_urls"], ensure_ascii=False),
            description=spec["description"],
            listed_at=spec["listed_at"],
        )
        db.add(complex_)
        await db.flush()
        created_complexes += 1

        for i, (year, month) in enumerate(months):
            drift = 1.0 + (i - 9) * 0.005
            for area in spec["areas"]:
                # denser history near recent months
                keep_prob = 0.55 if i > 10 else 0.35
                if rng.random() > keep_prob:
                    continue
                day = rng.randint(1, 27)
                if spec["deal_kind"] == "rent":
                    deposit = int(spec["base_deposit"] * drift * rng.uniform(0.94, 1.06))
                    monthly = max(10, int(spec["base_monthly"] * drift * rng.uniform(0.94, 1.06)))
                    price, rent = deposit, monthly
                else:
                    price = int(
                        spec["base_deposit"]
                        * (area / max(spec["areas"]))
                        * drift
                        * rng.uniform(0.94, 1.06)
                    )
                    rent = 0
                db.add(
                    Trade(
                        complex_id=complex_.id,
                        deal_date=date(year, month, day),
                        deal_year=year,
                        deal_month=month,
                        deal_kind=spec["deal_kind"],
                        exclusive_area=area,
                        price_manwon=price,
                        monthly_rent_manwon=rent,
                        floor=rng.randint(1, spec["floor_max"]),
                        dealing_gbn="중개거래",
                    )
                )
                created_trades += 1

    await db.commit()
    latest_trade = max(
        (date(y, m, 1) for y, m in months),
        default=date.today(),
    )
    return {
        "ok": True,
        "complexes": created_complexes,
        "trades": created_trades,
        "stations": len(SEOUL_STATIONS),
        "data_source": "demo",
        "data_as_of": latest_trade.strftime("%Y-%m"),
        "listed_as_of": latest_trade.strftime("%Y-%m"),
        "message": (
            f"데모 시드 {created_complexes}개·{created_trades}건. "
            f"거래일 형태는 실거래와 같지만 국토부 원본이 아닙니다 "
            f"(최신월≈{latest_trade.strftime('%Y-%m')}). "
            "진짜 실거래는 MOLIT_SERVICE_KEY 설정 후 POST /api/ingest."
        ),
        "latest_month_seed": latest_trade.strftime("%Y-%m"),
    }


@router.post("/seed")
async def seed_demo(db: AsyncSession = Depends(get_db), count: int = 160):
    return await run_demo_seed(db, count=count)
