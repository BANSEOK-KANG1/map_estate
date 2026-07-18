"""차세대 온비드 부동산 물건상세 → 권리·특약·감정평가 요약."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import AuctionLot

logger = logging.getLogger(__name__)

ONBID_DETAIL_URL = "https://apis.data.go.kr/B010003/OnbidRlstDtlSrvc2/getRlstDtlInf2"
ONBID_BID_INFO_URL = "https://apis.data.go.kr/B010003/OnbidCltrBidDtlSrvc2/getCltrBidInf2"
ONBID_BID_RSLT_URL = (
    "https://apis.data.go.kr/B010003/OnbidCltrBidRsltDtlSrvc2/getCltrBidRsltDtl2"
)


def _as_list(node: Any) -> list[Any]:
    if node is None:
        return []
    if isinstance(node, list):
        return node
    if isinstance(node, dict):
        inner = node.get("item")
        if inner is None:
            return [node]
        return inner if isinstance(inner, list) else [inner]
    return []


def _text(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def build_legal_summary(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize detail payload for API/UI."""
    etc = _text(item.get("cltrEtcCont"))
    util = _text(item.get("utlzPscdCont"))
    loc = _text(item.get("locVntyPscdCont"))
    eviction = _text(item.get("evcRsbyTrgtCont"))
    incidental = _text(item.get("icdlCdtnCont"))
    purchase_qual = _text(item.get("purrQlfcCont"))
    payment = _text(item.get("pytnMtrsCont"))

    leases = _as_list(item.get("leasInfList"))
    occupy = _as_list(item.get("ocpyRelList"))
    registry = _as_list(item.get("rgstPrmrInfList"))
    distribute = _as_list(item.get("dtbtRqrMtrsList"))
    appraisals = _as_list(item.get("apslEvlClgList"))

    risk_flags: list[str] = []
    blob = " ".join([etc, util, incidental, payment, purchase_qual])
    for kw in ("유치권", "법정지상권", "분묘", "가처분", "가등기", "임차권", "점유", "명도", "위반건축"):
        if kw in blob:
            risk_flags.append(kw)

    if leases:
        risk_flags.append(f"임대차 {len(leases)}건")
    if occupy:
        risk_flags.append(f"점유관계 {len(occupy)}건")
    if registry:
        risk_flags.append(f"등기관련 {len(registry)}건")

    appraisal_urls = []
    for a in appraisals:
        if isinstance(a, dict) and a.get("urlAdr"):
            appraisal_urls.append(
                {
                    "org": _text(a.get("apslEvlOrgNm")),
                    "date": _text(a.get("apslEvlYmd")),
                    "amount": a.get("apslEvlAmt"),
                    "url": _text(a.get("urlAdr")),
                }
            )

    notes: list[str] = []
    if etc:
        notes.append(f"기타: {etc}")
    if util:
        notes.append(f"이용현황: {util}")
    if loc:
        notes.append(f"위치·주변: {loc}")
    if eviction:
        notes.append(f"명도책임: {eviction}")
    if incidental:
        notes.append(f"부대조건: {incidental}")
    if purchase_qual:
        notes.append(f"매수자격: {purchase_qual}")
    if payment:
        notes.append(f"대금관련: {payment}")
    if not leases:
        notes.append("임대차 목록: API상 없음 (등기·현장 확인 필요)")
    if not occupy:
        notes.append("점유관계 목록: API상 없음 (현장 확인 필요)")
    if not registry:
        notes.append("등기·우선변제 목록: API상 없음 (등기부등본 확인 필요)")
    notes.append(
        "유치권·법정지상권 등 상세 권리는 OpenAPI만으로 확정되지 않습니다. "
        "감정평가서·등기부등본·원문 공고를 반드시 확인하세요."
    )

    try:
        fail_count = int(item.get("usbdNft") or 0)
    except (TypeError, ValueError):
        fail_count = 0

    return {
        "pbct_cdtn_no": item.get("pbctCdtnNo"),
        "org_name": _text(item.get("orgNm") or item.get("rqstOrgNm")),
        "fail_count": fail_count,
        "status_name": _text(item.get("pbctStatNm")),
        "eviction_target": eviction,
        "etc_note": etc,
        "utilization_note": util,
        "location_note": loc,
        "risk_flags": risk_flags,
        "notes": notes,
        "lease_count": len(leases),
        "occupy_count": len(occupy),
        "registry_count": len(registry),
        "distribute_count": len(distribute),
        "leases": leases[:20],
        "occupy": occupy[:20],
        "registry": registry[:20],
        "appraisals": appraisal_urls,
        "bid_rounds": [],  # filled when bid-info API is authorized
        "bid_result": None,
        "gaps": [
            "회차별 유찰가·입찰 참여팀 수: 물건상세 입찰정보 API 활용신청 필요",
            "낙찰/유찰 개찰 상세: 입찰결과상세 API 활용신청 필요",
        ],
    }


async def fetch_onbid_detail_item(
    settings: Settings,
    cltr_mng_no: str,
    pbct_cdtn_no: str | int | None = None,
) -> dict[str, Any] | None:
    if not settings.onbid_service_key or not cltr_mng_no:
        return None
    params: dict[str, Any] = {
        "serviceKey": settings.onbid_service_key,
        "pageNo": 1,
        "numOfRows": 10,
        "resultType": "json",
        "cltrMngNo": cltr_mng_no,
    }
    if pbct_cdtn_no:
        params["pbctCdtnNo"] = pbct_cdtn_no
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(ONBID_DETAIL_URL, params=params, timeout=40.0)
        if resp.status_code != 200:
            logger.warning("onbid detail HTTP %s: %s", resp.status_code, resp.text[:200])
            return None
        data = resp.json()
        header = data.get("header") or {}
        if str(header.get("resultCode") or "") not in ("00", "0", "000", "0000"):
            logger.warning("onbid detail error: %s", header)
            return None
        items = _as_list((data.get("body") or {}).get("items"))
        return items[0] if items and isinstance(items[0], dict) else None


async def try_fetch_bid_rounds(
    settings: Settings,
    cltr_mng_no: str,
    pbct_cdtn_no: str | int | None,
) -> tuple[list[dict[str, Any]], str | None]:
    """Returns (rounds, error). error='forbidden' if 403."""
    if not settings.onbid_service_key or not cltr_mng_no or not pbct_cdtn_no:
        return [], "missing_ids"
    params = {
        "serviceKey": settings.onbid_service_key,
        "pageNo": 1,
        "numOfRows": 50,
        "resultType": "json",
        "cltrMngNo": cltr_mng_no,
        "pbctCdtnNo": pbct_cdtn_no,
    }
    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(ONBID_BID_INFO_URL, params=params, timeout=30.0)
    except httpx.HTTPError as exc:
        return [], f"network:{exc}"
    if resp.status_code == 403:
        return [], "forbidden"
    if resp.status_code != 200:
        return [], f"http:{resp.status_code}"
    try:
        data = resp.json()
    except json.JSONDecodeError:
        return [], "parse"
    # Flexible parse — field names vary by guide version
    body = data.get("body") or data.get("response", {}).get("body") or {}
    items = _as_list(body.get("items") if isinstance(body, dict) else None)
    rounds: list[dict[str, Any]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        rounds.append(
            {
                "round_no": it.get("pbctNsq") or it.get("pbctsn") or it.get("roundNo"),
                "min_bid": it.get("lowstBidPrc") or it.get("lowstBidPrcIndctCont"),
                "bidder_count": it.get("bidNop")
                or it.get("bidPrtcpNop")
                or it.get("bidCnt")
                or it.get("tndrNop"),
                "result": it.get("pbctStatNm") or it.get("bidRsltNm") or "",
                "raw": {k: it.get(k) for k in list(it.keys())[:30]},
            }
        )
    return rounds, None


async def enrich_lot_onbid_detail(
    session: AsyncSession,
    settings: Settings,
    lot: AuctionLot,
) -> AuctionLot:
    if lot.source != "onbid" or not lot.external_id:
        return lot
    cltr = lot.external_id.split(":", 1)[0]
    pbct = getattr(lot, "pbct_cdtn_no", None) or None
    if not pbct and ":" in lot.external_id:
        pbct = lot.external_id.split(":", 1)[1]
    item = await fetch_onbid_detail_item(settings, cltr, pbct)
    if not item:
        return lot

    legal = build_legal_summary(item)
    pbct = item.get("pbctCdtnNo")
    if pbct is not None:
        lot.pbct_cdtn_no = str(pbct)
    if item.get("onbidCltrno"):
        from app.ingest.onbid import build_onbid_detail_url

        lot.source_url = build_onbid_detail_url(
            onbid_cltr_no=item.get("onbidCltrno"),
            onbid_pbanc_no=item.get("onbidPbancNo"),
            pbct_no=item.get("pbctNo"),
            pbct_cdtn_no=item.get("pbctCdtnNo") or pbct,
            prpt_div_cd=item.get("prptDivCd"),
        )

    rounds, err = await try_fetch_bid_rounds(settings, cltr, pbct)
    if rounds:
        legal["bid_rounds"] = rounds
        legal["gaps"] = [g for g in legal["gaps"] if "입찰정보" not in g]
    elif err == "forbidden":
        legal["bid_info_status"] = "forbidden"
    else:
        legal["bid_info_status"] = err or "empty"

    # Update fail count / description from authoritative detail
    if legal.get("fail_count") is not None:
        lot.fail_count = int(legal["fail_count"])
    if item.get("landSqms") is not None:
        try:
            lot.land_area = float(item["landSqms"])
        except (TypeError, ValueError):
            pass
    if item.get("bldSqms") is not None and not lot.exclusive_area:
        try:
            lot.exclusive_area = float(item["bldSqms"])
        except (TypeError, ValueError):
            pass

    photos = _as_list(item.get("potoUrlList"))
    urls = []
    for p in photos:
        if isinstance(p, str):
            urls.append(p)
        elif isinstance(p, dict):
            u = p.get("urlAdr") or p.get("url") or p.get("potoUrlAdr")
            if u:
                urls.append(str(u))
    if urls:
        lot.photo_urls = json.dumps(urls[:12], ensure_ascii=False)

    # Human-readable description for list/detail fallback
    lot.description = "\n".join(legal.get("notes") or [])[:2000]
    lot.court_name = legal.get("org_name") or lot.court_name
    lot.detail_json = json.dumps(legal, ensure_ascii=False)
    await session.flush()
    return lot
