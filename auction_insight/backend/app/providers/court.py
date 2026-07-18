"""법원 경매 데이터 어댑터.

공식 OpenAPI가 없어 MVP는 데모/CSV 주입용 인터페이스만 제공한다.
이후 합법 소스·제휴 API·수동 업로드로 구현체를 교체하면 된다.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any


@dataclass
class CourtLotDraft:
    external_id: str
    case_no: str
    title: str
    usage: str
    address: str
    exclusive_area: float | None
    appraisal_manwon: int | None
    min_bid_manwon: int | None
    fail_count: int
    status: str
    bid_end_at: datetime | None
    sale_date: date | None
    source_url: str
    description: str = ""
    schedules: list[dict[str, Any]] = field(default_factory=list)
    lat: float | None = None
    lng: float | None = None


class CourtAuctionProvider(ABC):
    """Swap this implementation when a real court data feed is available."""

    @abstractmethod
    async def fetch_lots(self, *, region_hint: str | None = None) -> list[CourtLotDraft]:
        raise NotImplementedError


class DemoCourtAuctionProvider(CourtAuctionProvider):
    """Static Seoul/Gyeonggi court auction samples for UI/dev."""

    async def fetch_lots(self, *, region_hint: str | None = None) -> list[CourtLotDraft]:
        now = datetime.utcnow()
        samples = [
            CourtLotDraft(
                external_id="court-2026-타경-1234",
                case_no="2026타경1234",
                title="강남구 역삼동 오피스텔",
                usage="오피스텔",
                address="서울특별시 강남구 역삼동 123-45",
                exclusive_area=29.8,
                appraisal_manwon=42000,
                min_bid_manwon=29400,
                fail_count=1,
                status="active",
                bid_end_at=now + timedelta(days=5),
                sale_date=(now + timedelta(days=5)).date(),
                source_url="https://www.courtauction.go.kr/",
                description="데모 경매 물건. 실제 법원 데이터 연동 전 샘플입니다.",
                schedules=[
                    {
                        "round_no": 1,
                        "sale_date": (now - timedelta(days=20)).date().isoformat(),
                        "min_bid_manwon": 33600,
                        "result": "유찰",
                    },
                    {
                        "round_no": 2,
                        "sale_date": (now + timedelta(days=5)).date().isoformat(),
                        "min_bid_manwon": 29400,
                        "result": "진행",
                    },
                ],
                lat=37.5007,
                lng=127.0365,
            ),
            CourtLotDraft(
                external_id="court-2025-타경-8891",
                case_no="2025타경8891",
                title="마포구 합정동 다가구",
                usage="다가구",
                address="서울특별시 마포구 합정동 390",
                exclusive_area=98.0,
                appraisal_manwon=98000,
                min_bid_manwon=62720,
                fail_count=2,
                status="active",
                bid_end_at=now + timedelta(days=12),
                sale_date=(now + timedelta(days=12)).date(),
                source_url="https://www.courtauction.go.kr/",
                description="데모 경매 물건.",
                schedules=[
                    {
                        "round_no": 1,
                        "sale_date": (now - timedelta(days=40)).date().isoformat(),
                        "min_bid_manwon": 78400,
                        "result": "유찰",
                    },
                    {
                        "round_no": 2,
                        "sale_date": (now - timedelta(days=14)).date().isoformat(),
                        "min_bid_manwon": 70560,
                        "result": "유찰",
                    },
                    {
                        "round_no": 3,
                        "sale_date": (now + timedelta(days=12)).date().isoformat(),
                        "min_bid_manwon": 62720,
                        "result": "진행",
                    },
                ],
                lat=37.5495,
                lng=126.9139,
            ),
            CourtLotDraft(
                external_id="court-2026-타경-441",
                case_no="2026타경441",
                title="성남시 분당구 정자동 아파트",
                usage="아파트",
                address="경기도 성남시 분당구 정자동 10",
                exclusive_area=84.9,
                appraisal_manwon=125000,
                min_bid_manwon=100000,
                fail_count=0,
                status="active",
                bid_end_at=now + timedelta(days=18),
                sale_date=(now + timedelta(days=18)).date(),
                source_url="https://www.courtauction.go.kr/",
                description="데모 경매 물건 (경기).",
                schedules=[
                    {
                        "round_no": 1,
                        "sale_date": (now + timedelta(days=18)).date().isoformat(),
                        "min_bid_manwon": 100000,
                        "result": "진행",
                    },
                ],
                lat=37.3650,
                lng=127.1080,
            ),
            CourtLotDraft(
                external_id="court-2025-타경-2201",
                case_no="2025타경2201",
                title="수원시 영통구 원룸",
                usage="다세대",
                address="경기도 수원시 영통구 영통동 955",
                exclusive_area=42.5,
                appraisal_manwon=28000,
                min_bid_manwon=17920,
                fail_count=2,
                status="active",
                bid_end_at=now + timedelta(days=3),
                sale_date=(now + timedelta(days=3)).date(),
                source_url="https://www.courtauction.go.kr/",
                description="데모 경매 물건 (경기).",
                schedules=[
                    {
                        "round_no": 1,
                        "sale_date": (now - timedelta(days=35)).date().isoformat(),
                        "min_bid_manwon": 22400,
                        "result": "유찰",
                    },
                    {
                        "round_no": 2,
                        "sale_date": (now - timedelta(days=10)).date().isoformat(),
                        "min_bid_manwon": 20160,
                        "result": "유찰",
                    },
                    {
                        "round_no": 3,
                        "sale_date": (now + timedelta(days=3)).date().isoformat(),
                        "min_bid_manwon": 17920,
                        "result": "진행",
                    },
                ],
                lat=37.2526,
                lng=127.0713,
            ),
        ]
        if region_hint:
            samples = [s for s in samples if region_hint in s.address]
        return samples
