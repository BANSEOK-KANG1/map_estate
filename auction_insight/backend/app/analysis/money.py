"""Money helpers: won canonical, multi-unit display, digit-error detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MoneyTriple:
    won: int
    manwon: float
    eok: float
    label_won: str
    label_manwon: str
    label_eok: str


def to_triple(won: int | None) -> MoneyTriple | None:
    if won is None:
        return None
    man = won / 10_000
    eok = won / 100_000_000
    return MoneyTriple(
        won=won,
        manwon=man,
        eok=eok,
        label_won=f"{won:,}원",
        label_manwon=_fmt_man(man),
        label_eok=_fmt_eok(eok),
    )


def _fmt_man(man: float) -> str:
    if abs(man - round(man)) < 1e-9:
        return f"{int(round(man)):,}만원"
    return f"{man:,.1f}만원"


def _fmt_eok(eok: float) -> str:
    if abs(eok) < 0.01:
        return "0억원"
    if abs(eok - round(eok, 1)) < 1e-9:
        return f"{eok:.1f}억원"
    return f"{eok:.2f}억원"


def parse_user_amount(
    *,
    raw: str | int | float | None,
    unit: str = "won",
) -> int | None:
    """Parse user input into won. unit: won | manwon | eok."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, str):
        cleaned = raw.replace(",", "").replace("원", "").replace("만", "").replace("억", "").strip()
        if not cleaned:
            return None
        value = float(cleaned)
    else:
        value = float(raw)
    if unit == "manwon":
        return int(round(value * 10_000))
    if unit == "eok":
        return int(round(value * 100_000_000))
    return int(round(value))


def detect_digit_errors(
    *,
    appraisal_won: int | None = None,
    min_bid_won: int | None = None,
    planned_price_won: int | None = None,
) -> list[dict[str, str]]:
    """
    Catch classic 10x mistakes e.g. 40,200,000 vs 402,000,000.
    Deterministic heuristics only — never auto-correct.
    """
    warnings: list[dict[str, str]] = []
    amounts = {
        "appraisal": appraisal_won,
        "min_bid": min_bid_won,
        "planned_price": planned_price_won,
    }
    present = {k: v for k, v in amounts.items() if v is not None and v > 0}
    if len(present) < 2:
        # single amount: flag if looks like manwon typed as won for housing
        for k, v in present.items():
            if 1_000_000 <= v < 50_000_000:
                warnings.append(
                    {
                        "code": "POSSIBLE_MANWON_AS_WON",
                        "field": k,
                        "message": (
                            f"{k}={v:,}원 은 주택 기준으로 낮아 보일 수 있습니다. "
                            f"만원 단위 입력을 원 단위로 잘못 넣했는지 확인하세요 "
                            f"(예: 4,020만원→40,200,000원 vs 4억20만→402,000,000원)."
                        ),
                    }
                )
        return warnings

    pairs = list(present.items())
    for i in range(len(pairs)):
        for j in range(i + 1, len(pairs)):
            a_name, a = pairs[i]
            b_name, b = pairs[j]
            hi, lo = (a, b) if a >= b else (b, a)
            hi_n, lo_n = (a_name, b_name) if a >= b else (b_name, a_name)
            ratio = hi / lo if lo else 0
            # exact-ish factor of 10
            for factor in (10, 100):
                if 0.95 * factor <= ratio <= 1.05 * factor:
                    alt_lo = lo * factor
                    warnings.append(
                        {
                            "code": "DIGIT_FACTOR",
                            "field": f"{lo_n}/{hi_n}",
                            "message": (
                                f"{lo_n}={lo:,}원 과 {hi_n}={hi:,}원 비율이 약 {factor}배입니다. "
                                f"자릿수 오류 가능: {lo_n}를 {alt_lo:,}원으로 의도했는지 확인하세요."
                            ),
                        }
                    )
            # min_bid >> appraisal (unusual unless typo)
            if a_name == "min_bid" and b_name == "appraisal" and a > b * 1.2:
                warnings.append(
                    {
                        "code": "MIN_ABOVE_APPRAISAL",
                        "field": "min_bid",
                        "message": "최저가가 감정가보다 높습니다. 단위(원/만원) 혼동을 확인하세요.",
                    }
                )
            if b_name == "min_bid" and a_name == "appraisal" and b > a * 1.2:
                warnings.append(
                    {
                        "code": "MIN_ABOVE_APPRAISAL",
                        "field": "min_bid",
                        "message": "최저가가 감정가보다 높습니다. 단위(원/만원) 혼동을 확인하세요.",
                    }
                )
    return warnings


def triple_dict(won: int | None) -> dict | None:
    t = to_triple(won)
    if t is None:
        return None
    return {
        "won": t.won,
        "manwon": t.manwon,
        "eok": t.eok,
        "label_won": t.label_won,
        "label_manwon": t.label_manwon,
        "label_eok": t.label_eok,
    }
