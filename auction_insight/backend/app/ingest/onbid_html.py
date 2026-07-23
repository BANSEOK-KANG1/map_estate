"""Parse Onbid detail HTML for previous bid history (이전 입찰내역).

Public bid-info APIs often return 403; the detail page already embeds the timeline.
"""

from __future__ import annotations

import re
from typing import Any

import httpx

_WON_RE = re.compile(r"([0-9,]+)\s*원")


def _won_to_manwon(text: str) -> int | None:
    m = _WON_RE.search(text.replace(" ", ""))
    if not m:
        return None
    try:
        won = int(m.group(1).replace(",", ""))
    except ValueError:
        return None
    return max(0, won // 10_000)


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def parse_bid_history_html(html: str) -> dict[str, Any]:
    """Extract summary + timeline rows from Onbid 물건상세 HTML."""
    if not html or "이전 입찰내역" not in html:
        return {"summary": "", "rounds": [], "notes": [], "source": "html"}

    sec = html.split("이전 입찰내역", 1)[1]
    for stop in ("인근 시세", "권리분석", "관련문서", "공매일정", "물건위치"):
        if stop in sec:
            sec = sec.split(stop, 1)[0]
            break

    summary_m = re.search(
        r"전체 입찰내역</span>\s*<span class=\"txt01\">([^<]+)</span>",
        html,
    )
    summary = _clean(summary_m.group(1)) if summary_m else ""

    # Latest previous result / min price chips
    prev_result_m = re.search(
        r"이전 입찰 결과</span>\s*<span class=\"txt01\">\s*([^<]+)</span>",
        html,
    )
    prev_min_m = re.search(
        r"이전 입찰 최저입찰가격</span>\s*<span class=\"txt01\">\s*([^<]+)</span>",
        html,
    )

    blocks = re.findall(r'<div class="history_item[^"]*">(.*?)</button>', sec, re.S)
    rounds: list[dict[str, Any]] = []
    for b in blocks:
        stat_m = re.search(r'class="stat_txt01">\s*([^<]+)\s*</span>', b)
        date_m = re.search(r"개찰일시\s*:\s*([^<]+)</span>", b)
        round_m = re.search(r">회차</span>\s*<span class=\"txt01\">\s*([^<]+)</span>", b)
        planned_m = re.search(
            r"공매예정가격\s*</span>\s*<span class=\"txt01\">\s*([^<]+)</span>",
            b,
        )
        win_m = re.search(
            r"낙찰금액</span>\s*<span class=\"txt0[12]\">\s*([^<]*?)\s*</span>",
            b,
        )
        planned_txt = _clean(planned_m.group(1)) if planned_m else ""
        win_txt = _clean(win_m.group(1)) if win_m else ""
        if win_txt in {"-", "—", ""}:
            win_txt = ""
        rounds.append(
            {
                "result": _clean(stat_m.group(1)) if stat_m else "",
                "open_at": _clean(date_m.group(1)) if date_m else "",
                "round_label": _clean(round_m.group(1)) if round_m else "",
                "planned_price_text": planned_txt,
                "planned_manwon": _won_to_manwon(planned_txt),
                "win_price_text": win_txt,
                "win_manwon": _won_to_manwon(win_txt) if win_txt else None,
                "min_bid": planned_txt,
                "bidder_count": None,
                "source": "onbid_html",
            }
        )

    notes = build_bid_history_notes(
        rounds,
        summary=summary,
        prev_result=_clean(prev_result_m.group(1)) if prev_result_m else "",
        prev_min=_clean(prev_min_m.group(1)) if prev_min_m else "",
    )
    return {
        "summary": summary,
        "prev_result": _clean(prev_result_m.group(1)) if prev_result_m else "",
        "prev_min_price": _clean(prev_min_m.group(1)) if prev_min_m else "",
        "rounds": rounds,
        "notes": notes,
        "source": "onbid_html",
    }


def build_bid_history_notes(
    rounds: list[dict[str, Any]],
    *,
    summary: str = "",
    prev_result: str = "",
    prev_min: str = "",
) -> list[str]:
    """Human notes: 낙찰 후 재공매 등. 확정이 아닌 해석 힌트."""
    notes: list[str] = []
    if summary:
        notes.append(f"온비드 이전 입찰 요약: {summary}")
    if prev_result:
        line = f"직전 회차 결과: {prev_result}"
        if prev_min:
            line += f" · 최저/예정가 {prev_min}"
        notes.append(line)

    won = [r for r in rounds if "낙찰" in str(r.get("result") or "")]
    if won:
        for w in won[:3]:
            amt = w.get("win_price_text") or w.get("planned_price_text") or ""
            when = w.get("open_at") or ""
            notes.append(
                f"낙찰 이력 {when} · {w.get('round_label') or ''} · {amt}".strip(" ·")
            )
        notes.append(
            "낙찰 이후에도 공매가 이어진 경우, 대금 미납·매각결정 취소·압류해제 등으로 "
            "재공매된 패턴일 수 있습니다. 사유는 온비드 상세·원문으로 확인하세요."
        )

    cancel_n = sum(1 for r in rounds if "취소" in str(r.get("result") or ""))
    fail_n = sum(1 for r in rounds if "유찰" in str(r.get("result") or ""))
    if cancel_n and fail_n:
        notes.append(
            f"타임라인상 유찰 {fail_n}회 · 취소 {cancel_n}회가 섞여 있습니다. "
            "취소는 공매 중단·재공고와 관련될 수 있어 단순 유찰과 구분하세요."
        )
    return notes


async def fetch_onbid_html(url: str, *, timeout: float = 35.0) -> str:
    if not url:
        return ""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; AuctionInsight/1.0; +https://map.measuremkt.com)"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
        resp = await client.get(url, timeout=timeout)
        if resp.status_code != 200:
            return ""
        return resp.text or ""
