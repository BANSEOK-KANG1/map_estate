"""캠코 온비드 공매 물건 수집.

기본: 차세대 온비드 (apis.data.go.kr) — openapi.onbid.co.kr 장애 시에도 동작.
폴백: 기존 openapi.onbid.co.kr 캠코 공매목록.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any
from xml.etree.ElementTree import Element

import httpx
from defusedxml import ElementTree as ET
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.data.regions import ONBID_SIDO_NAMES, TARGET_SIDO_PREFIXES
from app.models import AuctionLot, AuctionSchedule, IngestRun
from app.services.lots import match_region_code

logger = logging.getLogger(__name__)

# 차세대 온비드 부동산 물건목록 (공공데이터포털 게이트웨이)
ONBID_NEXTGEN_LIST_URL = (
    "https://apis.data.go.kr/B010003/OnbidRlstListSrvc2/getRlstCltrList2"
)

# 레거시 캠코 공매물건목록 (종종 ConnectTimeout)
ONBID_LEGACY_LIST_URL = (
    "http://openapi.onbid.co.kr/openapi/services/KamcoPblsalThingInquireSvc/getKamcoPbctCltrList"
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AuctionInsight/1.0; +https://github.com/local/auction_insight)"
    ),
    "Accept": "application/json, application/xml, text/xml, */*",
}


def build_onbid_detail_url(
    *,
    onbid_cltr_no: Any,
    onbid_pbanc_no: Any,
    pbct_no: Any,
    pbct_cdtn_no: Any,
    prpt_div_cd: Any = "0005",
) -> str:
    """차세대 온비드 물건상세 딥링크 (브라우저 GET 가능)."""
    from urllib.parse import urlencode

    if not onbid_cltr_no or not onbid_pbanc_no or not pbct_no or not pbct_cdtn_no:
        return "https://www.onbid.co.kr/op/meminf/lgnmng/prtllgn/PrtlLgnController/main.do"
    q = urlencode(
        {
            "onbidCltrno": str(onbid_cltr_no),
            "onbidPbancNo": str(onbid_pbanc_no),
            "pbctNo": str(pbct_no),
            "pbctCdtnNo": str(pbct_cdtn_no),
            "cltrPrptDivCd": str(prpt_div_cd or "0005"),
        }
    )
    return (
        "https://www.onbid.co.kr/op/cltrpbancinf/cltrdtl/"
        f"CltrDtlController/mvmnCltrDtl.do?{q}"
    )


def _text(el: Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text.strip()


def _first(item: Element, tags: list[str], default: str = "") -> str:
    for tag in tags:
        val = _text(item.find(tag))
        if val:
            return val
    return default


def _parse_won_to_manwon(raw: str) -> int | None:
    digits = "".join(c for c in raw if c.isdigit())
    if not digits:
        return None
    won = int(digits)
    # Onbid often returns 원 단위
    if won >= 10_000:
        return won // 10_000
    return won


def _in_target_area(address: str) -> bool:
    return any(p in address for p in TARGET_SIDO_PREFIXES)


def _parse_datetime(raw: str) -> datetime | None:
    raw = str(raw or "").strip()
    if not raw:
        return None
    # 차세대 플레이스홀더 (입찰 미정)
    if raw.startswith("2999"):
        return None
    digits = "".join(c for c in raw if c.isdigit())
    for fmt, n in (
        ("%Y%m%d%H%M%S", 14),
        ("%Y%m%d%H%M", 12),
        ("%Y%m%d", 8),
    ):
        if len(digits) >= n:
            try:
                return datetime.strptime(digits[:n], fmt)
            except ValueError:
                pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(raw[:19] if " " in fmt else raw[: len(raw)], fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", ""))
    except ValueError:
        return None


def _won_field_to_manwon(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        won = int(value)
        return won // 10_000 if won >= 10_000 else won
    return _parse_won_to_manwon(str(value))


def parse_nextgen_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    body = payload.get("body") or {}
    items_node = (body.get("items") or {}).get("item")
    if items_node is None:
        return []
    if isinstance(items_node, dict):
        items_node = [items_node]

    out: list[dict[str, Any]] = []
    for item in items_node:
        if not isinstance(item, dict):
            continue
        external_id = str(item.get("cltrMngNo") or item.get("onbidCltrno") or "").strip()
        if not external_id:
            continue
        pbct = item.get("pbctCdtnNo")
        # 동일 물건번호 + 다른 공매조건이 목록에 반복됨 → 조건까지 키로 사용
        if pbct is not None and str(pbct).strip():
            external_id = f"{external_id}:{pbct}"
        title = str(item.get("onbidCltrNm") or "").strip()
        sido = str(item.get("lctnSdnm") or "").strip()
        sgg = str(item.get("lctnSggnm") or "").strip()
        emd = str(item.get("lctnEmdNm") or "").strip()
        address = title or " ".join(p for p in (sido, sgg, emd) if p)
        usage = (
            str(item.get("cltrUsgSclsCtgrNm") or "").strip()
            or str(item.get("cltrUsgMclsCtgrNm") or "").strip()
            or str(item.get("cltrUsgLclsCtgrNm") or "").strip()
            or "부동산"
        )
        area = item.get("bldSqms")
        try:
            area_f = float(area) if area is not None else None
        except (TypeError, ValueError):
            area_f = None
        min_bid = _won_field_to_manwon(
            item.get("lowstBidPrcIndctCont") or item.get("frstBidPrc")
        )
        appraisal = _won_field_to_manwon(item.get("apslEvlAmt"))
        try:
            fail_count = int(item.get("usbdNft") or 0)
        except (TypeError, ValueError):
            fail_count = 0
        cltr_only = str(item.get("cltrMngNo") or "").strip()
        onbid_cltr_no = item.get("onbidCltrno")
        onbid_pbanc_no = item.get("onbidPbancNo")
        pbct_no = item.get("pbctNo")
        prpt_div_cd = item.get("prptDivCd") or "0005"
        out.append(
            {
                "external_id": external_id,
                "cltr_mng_no": cltr_only,
                "case_no": str(pbct_no or cltr_only or external_id),
                "title": title or address,
                "usage": usage,
                "address": address,
                "exclusive_area": area_f,
                "appraisal_manwon": appraisal,
                "min_bid_manwon": min_bid,
                "fail_count": fail_count,
                "bid_start_at": _parse_datetime(str(item.get("cltrBidBgngDt") or "")),
                "bid_end_at": _parse_datetime(str(item.get("cltrBidEndDt") or "")),
                "source_url": build_onbid_detail_url(
                    onbid_cltr_no=onbid_cltr_no,
                    onbid_pbanc_no=onbid_pbanc_no,
                    pbct_no=pbct_no,
                    pbct_cdtn_no=pbct,
                    prpt_div_cd=prpt_div_cd,
                ),
                "onbid_cltr_no": str(onbid_cltr_no or ""),
                "onbid_pbanc_no": str(onbid_pbanc_no or ""),
                "pbct_no": str(pbct_no or ""),
                "prpt_div_cd": str(prpt_div_cd or ""),
                "pbct_cdtn_no": str(pbct or ""),
                "_provider": "nextgen",
            }
        )
    return out


def parse_list_items(xml_text: str) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_text)
    items: list[dict[str, Any]] = []
    # handle both item / body/items/item shapes
    candidates = root.findall(".//item")
    for item in candidates:
        address = _first(
            item,
            ["LDNM_ADRS", "ADRS", "ADDR", "LCT_NM", "CLTR_NM"],
        )
        title = _first(item, ["CLTR_NM", "BID_NM", "PBCT_CLTR_NM"], address)
        external_id = _first(
            item,
            ["CLTR_MNMT_NO", "PLNM_NO", "PBCT_NO", "CLTR_NO"],
        )
        if not external_id:
            continue
        appraisal = _parse_won_to_manwon(
            _first(item, ["APSL_ASES_AMT", "APSL_AMT", "APPR_AMT"])
        )
        min_bid = _parse_won_to_manwon(
            _first(item, ["MIN_BID_PRC", "PBCT_BEGN_PRC", "LOW_PRC", "MIN_BID_AMT"])
        )
        area_raw = _first(item, ["AREA", "EXC_AREA", "BLDG_AREA", "TQTY_UT_NM"])
        area = None
        try:
            area = float("".join(c for c in area_raw if c.isdigit() or c == ".")) if area_raw else None
        except ValueError:
            area = None
        bid_end = _parse_datetime(
            _first(item, ["PBCT_CLSG_DT", "BID_CLSG_DT", "CLSG_DT", "PBCT_END_DT"])
        )
        bid_start = _parse_datetime(
            _first(item, ["PBCT_BEGN_DT", "BID_BEGN_DT", "BEGN_DT"])
        )
        usage = _first(item, ["CTGR_FULL_NM", "CTGR_NM", "USG"], "부동산")
        fail_raw = _first(item, ["PQNC_CNT", "FAIL_CNT", "USCBD_CNT"], "0")
        try:
            fail_count = int("".join(c for c in fail_raw if c.isdigit()) or "0")
        except ValueError:
            fail_count = 0
        case_no = _first(item, ["PLNM_NO", "PBCT_NO", "BID_NO"], external_id)
        items.append(
            {
                "external_id": external_id,
                "case_no": case_no,
                "title": title,
                "usage": usage,
                "address": address,
                "exclusive_area": area,
                "appraisal_manwon": appraisal,
                "min_bid_manwon": min_bid,
                "fail_count": fail_count,
                "bid_start_at": bid_start,
                "bid_end_at": bid_end,
                "source_url": f"https://www.onbid.co.kr/op/cta/qri/ctaRcarDtl.do?cltrMnmtNo={external_id}",
            }
        )
    return items


async def fetch_onbid_page_nextgen(
    client: httpx.AsyncClient,
    settings: Settings,
    page: int,
    page_size: int,
    *,
    lctn_sdnm: str | None = None,
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {
        "serviceKey": settings.onbid_service_key,
        "numOfRows": page_size,
        "pageNo": page,
        "resultType": "json",
        # 압류재산, 기타일반, 국유, 공유
        "prptDivCd": "0007,0005,0010,0002",
        "pvctTrgtYn": "N",
    }
    if lctn_sdnm:
        params["lctnSdnm"] = lctn_sdnm
    await asyncio.sleep(0.2)
    resp = await client.get(ONBID_NEXTGEN_LIST_URL, params=params, timeout=45.0)
    if resp.status_code != 200:
        raise RuntimeError(f"차세대 온비드 HTTP {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    header = data.get("header") or {}
    code = str(header.get("resultCode") or "")
    if code not in ("00", "0", "000", "0000"):
        raise RuntimeError(
            f"차세대 온비드 오류: {header.get('resultMsg') or code or resp.text[:200]}"
        )
    return parse_nextgen_items(data)


async def fetch_onbid_page_legacy(
    client: httpx.AsyncClient,
    settings: Settings,
    page: int,
    page_size: int,
) -> list[dict[str, Any]]:
    params = {
        "serviceKey": settings.onbid_service_key,
        "numOfRows": page_size,
        "pageNo": page,
        "DPSL_MTD_CD": "0001",
    }
    await asyncio.sleep(0.35)
    resp = await client.get(ONBID_LEGACY_LIST_URL, params=params, timeout=20.0)
    if resp.status_code != 200:
        logger.warning("onbid legacy HTTP %s: %s", resp.status_code, resp.text[:300])
        return []
    text = resp.text
    if "SERVICE_KEY" in text.upper() and "ERROR" in text.upper():
        logger.warning("onbid legacy key/error: %s", text[:300])
        return []
    return parse_list_items(text)


async def fetch_onbid_page(
    settings: Settings,
    page: int,
    page_size: int = 100,
    *,
    prefer_nextgen: bool = True,
    lctn_sdnm: str | None = None,
) -> list[dict[str, Any]]:
    if not settings.onbid_service_key:
        raise RuntimeError("ONBID_SERVICE_KEY is not set")

    async with httpx.AsyncClient(headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        errors: list[str] = []
        if prefer_nextgen:
            try:
                return await fetch_onbid_page_nextgen(
                    client, settings, page, page_size, lctn_sdnm=lctn_sdnm
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("nextgen onbid failed, trying legacy: %s", exc)
                errors.append(f"nextgen: {exc}")

        try:
            return await fetch_onbid_page_legacy(client, settings, page, page_size)
        except httpx.ConnectTimeout as exc:
            raise RuntimeError(
                "온비드 레거시 OpenAPI(openapi.onbid.co.kr) 연결 시간 초과. "
                "차세대 API(apis.data.go.kr)도 실패했습니다. "
                + ("; ".join(errors) if errors else "")
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError("온비드 OpenAPI 요청 시간 초과") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"온비드 OpenAPI HTTP 오류: {exc}") from exc


async def upsert_onbid_lot(session: AsyncSession, raw: dict[str, Any]) -> AuctionLot | None:
    address = raw.get("address") or ""
    if address and not _in_target_area(address):
        return None
    # if no address, keep and try later via geocode region
    external_id = raw["external_id"]
    result = await session.execute(
        select(AuctionLot).where(
            AuctionLot.source == "onbid",
            AuctionLot.external_id == external_id,
        )
    )
    lot = result.scalar_one_or_none()
    if lot is None:
        lot = AuctionLot(source="onbid", external_id=external_id)
        session.add(lot)

    lot.case_no = raw.get("case_no") or external_id
    lot.title = raw.get("title") or address
    lot.usage = raw.get("usage") or "부동산"
    lot.address = address
    lot.region_code = match_region_code(address)
    lot.exclusive_area = raw.get("exclusive_area")
    lot.appraisal_manwon = raw.get("appraisal_manwon")
    lot.min_bid_manwon = raw.get("min_bid_manwon")
    lot.fail_count = int(raw.get("fail_count") or 0)
    lot.status = "active"
    lot.bid_start_at = raw.get("bid_start_at")
    lot.bid_end_at = raw.get("bid_end_at")
    if lot.bid_end_at:
        lot.sale_date = lot.bid_end_at.date()
    lot.source_url = raw.get("source_url") or ""
    if raw.get("pbct_cdtn_no"):
        lot.pbct_cdtn_no = str(raw["pbct_cdtn_no"])
    # keep numeric onbid id in description prefix only if needed — prefer source_url
    await session.flush()

    # schedule snapshot for current round
    if lot.min_bid_manwon is not None:
        round_no = max(1, lot.fail_count + 1)
        existing = await session.execute(
            select(AuctionSchedule).where(
                AuctionSchedule.lot_id == lot.id,
                AuctionSchedule.round_no == round_no,
            )
        )
        sched = existing.scalar_one_or_none()
        if sched is None:
            sched = AuctionSchedule(lot_id=lot.id, round_no=round_no)
            session.add(sched)
        sched.sale_date = lot.sale_date
        sched.min_bid_manwon = lot.min_bid_manwon
        sched.result = "진행"
    from app.services.score import apply_lot_scores

    apply_lot_scores(lot)
    return lot


async def ingest_onbid(
    session: AsyncSession,
    settings: Settings,
    *,
    max_pages: int = 10,
    page_size: int = 100,
) -> IngestRun:
    """서울·경기·인천을 시도별로 수집 (lctnSdnm 필터)."""
    upserted = 0
    messages: list[str] = ["provider=nextgen(sido)"]
    try:
        for sido in ONBID_SIDO_NAMES:
            sido_kept = 0
            for page in range(1, max_pages + 1):
                items = await fetch_onbid_page(
                    settings, page, page_size, lctn_sdnm=sido
                )
                if not items:
                    messages.append(f"{sido} p{page}: empty")
                    break
                kept = 0
                for raw in items:
                    lot = await upsert_onbid_lot(session, raw)
                    if lot is not None:
                        kept += 1
                        upserted += 1
                sido_kept += kept
                messages.append(f"{sido} p{page}: {kept}/{len(items)}")
                await session.commit()
                # 마지막 페이지가 page_size 미만이면 종료
                if len(items) < page_size:
                    break
            messages.append(f"{sido} subtotal={sido_kept}")
        run = IngestRun(
            source="onbid",
            status="ok",
            lot_count=upserted,
            message="; ".join(messages)[:500],
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("onbid ingest failed")
        run = IngestRun(
            source="onbid",
            status="error",
            lot_count=upserted,
            message=str(exc)[:500],
        )
    session.add(run)
    await session.commit()
    return run
