"""RuleConfig seed & lookup — no hardcoded LTV/tax in business logic."""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.models import RuleConfig

# Seed values are examples with explicit source placeholders.
# Production must update effective_from / source_url when official rules change.
_SEED: list[dict] = [
    {
        "rule_key": "acquisition_tax_rate_housing",
        "effective_from": date(2024, 1, 1),
        "region_code": "*",
        "usage": "주택",
        "value_json": json.dumps({"rate": 0.011, "note": "1주택 가정 러프 — 공식 확인 필요"}),
        "source_url": "https://www.nts.go.kr",
        "source_label": "국세청(취득세 관련 안내 — 적용 전 최신 고시 확인)",
        "notes": "하드코딩 금지 원칙: 실제 세율은 지역·주택수·가액에 따라 달라짐. UNKNOWN 가능.",
    },
    {
        "rule_key": "ltv_cap_housing",
        "effective_from": date(2024, 1, 1),
        "region_code": "*",
        "usage": "주택",
        "value_json": json.dumps(
            {
                "conservative": 0.40,
                "base": 0.50,
                "optimistic": 0.60,
                "note": "정책·담보·차주 조건에 따라 변동. 확정 아님.",
            }
        ),
        "source_url": "https://www.fsc.go.kr",
        "source_label": "금융위원회 등 대출규제 안내(적용일·지역 확인 필수)",
        "notes": "대출한도는 범위로만 표시.",
    },
    {
        "rule_key": "required_docs_court",
        "effective_from": date(2024, 1, 1),
        "region_code": "*",
        "usage": "*",
        "value_json": json.dumps(
            {
                "docs": [
                    "registry",
                    "appraisal",
                    "sale_spec",
                ]
            }
        ),
        "source_url": "https://www.courtauction.go.kr",
        "source_label": "법원경매정보 — 매각물건명세서·감정평가서·등기 확인 관행",
        "notes": "필수문서 없으면 권리 확정 금지.",
    },
    {
        "rule_key": "required_docs_onbid",
        "effective_from": date(2024, 1, 1),
        "region_code": "*",
        "usage": "*",
        "value_json": json.dumps(
            {
                "docs": [
                    "registry",
                    "appraisal",
                    "onbid_notice",
                ]
            }
        ),
        "source_url": "https://www.onbid.co.kr",
        "source_label": "온비드 공고·특약·감정평가",
        "notes": "공매는 조세 법정기일·배분 로직을 법원 말소기준과 분리.",
    },
]


async def seed_rules(session: AsyncSession) -> int:
    added = 0
    for row in _SEED:
        existing = (
            await session.execute(
                select(RuleConfig).where(
                    RuleConfig.rule_key == row["rule_key"],
                    RuleConfig.effective_from == row["effective_from"],
                    RuleConfig.region_code == row["region_code"],
                    RuleConfig.usage == row["usage"],
                )
            )
        ).scalar_one_or_none()
        if existing:
            continue
        session.add(RuleConfig(**row))
        added += 1
    if added:
        await session.commit()
    return added


async def get_rule(
    session: AsyncSession,
    rule_key: str,
    *,
    on_date: date | None = None,
    region_code: str = "*",
    usage: str = "*",
) -> RuleConfig | None:
    on_date = on_date or date.today()
    rows = (
        await session.execute(
            select(RuleConfig)
            .where(
                RuleConfig.rule_key == rule_key,
                RuleConfig.effective_from <= on_date,
            )
            .order_by(RuleConfig.effective_from.desc())
        )
    ).scalars().all()
    # prefer exact region/usage, else wildcard
    for r in rows:
        if r.region_code in (region_code, "*") and r.usage in (usage, "*", "주택"):
            if r.region_code == region_code or r.region_code == "*":
                return r
    return rows[0] if rows else None
