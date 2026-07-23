"""재개발·정비사업 수집.

1) 기존 MOLIT_SERVICE_KEY로 전국 표준 OpenAPI 시도
2) 키 미등록/실패 시 data.go.kr 공개 CSV(로그인·키 불필요) 폴백
"""

from __future__ import annotations

import asyncio
import csv
import io
import logging
import re
from datetime import date, datetime
from typing import Any
from xml.etree.ElementTree import Element

import httpx
from defusedxml import ElementTree as ET
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import IngestRun
from app.services.insights import external_id_hash, normalize_sido, upsert_insight

logger = logging.getLogger(__name__)

REDEV_API_URL = (
    "https://api.data.go.kr/openapi/tn_pubr_public_redevelopment_reconstruction_project_api"
)

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; AuctionInsight/1.0; +https://github.com/local/auction_insight)"
    ),
    "Accept": "application/json, application/xml, text/xml, text/csv, */*",
}

# 키 없이 다운로드 가능한 지자체 CSV (서울·경기·인천 MVP)
# page: data.go.kr fileData 상세 → atchFileId 동적 해석
CSV_FALLBACK_PAGES: list[dict[str, str]] = [
    {
        "sido": "서울",
        "page_id": "15107957",
        "label": "서울 성북구 뉴타운·정비",
        "source_url": "https://www.data.go.kr/data/15107957/fileData.do",
    },
    {
        "sido": "서울",
        "page_id": "15131985",
        "label": "서울 서초구 재건축",
        "source_url": "https://www.data.go.kr/data/15131985/fileData.do",
    },
    {
        "sido": "서울",
        "page_id": "15113886",
        "label": "서울 강남구 주택건설·정비",
        "source_url": "https://www.data.go.kr/data/15113886/fileData.do",
    },
    {
        "sido": "경기",
        "page_id": "15051011",
        "label": "경기도 부천시 도시정비사업",
        "source_url": "https://www.data.go.kr/data/15051011/fileData.do",
    },
    {
        "sido": "경기",
        "page_id": "15085976",
        "label": "경기도 고양시 주택재개발",
        "source_url": "https://www.data.go.kr/data/15085976/fileData.do",
    },
    {
        "sido": "경기",
        "page_id": "15150142",
        "label": "경기도 안양시 정비사업",
        "source_url": "https://www.data.go.kr/data/15150142/fileData.do",
    },
    {
        "sido": "경기",
        "page_id": "15151267",
        "label": "경기도 남양주시 정비사업",
        "source_url": "https://www.data.go.kr/data/15151267/fileData.do",
    },
    {
        "sido": "인천",
        "page_id": "15055212",
        "label": "인천광역시 도시·주거환경 정비사업",
        "source_url": "https://www.data.go.kr/data/15055212/fileData.do",
    },
    {
        "sido": "인천",
        "page_id": "15072776",
        "label": "인천광역시 소규모주택정비",
        "source_url": "https://www.data.go.kr/data/15072776/fileData.do",
    },
    {
        "sido": "인천",
        "page_id": "15048913",
        "label": "인천광역시 도시개발사업",
        "source_url": "https://www.data.go.kr/data/15048913/fileData.do",
    },
]


def _text(el: Element | None, default: str = "") -> str:
    if el is None or el.text is None:
        return default
    return el.text.strip()


def _pick(d: dict[str, Any], *keys: str, default: str = "") -> str:
    for k in keys:
        v = d.get(k)
        if v is None:
            continue
        s = str(v).strip()
        if s and s.lower() != "null":
            return s
    return default


def _parse_ymd(raw: str) -> date | None:
    s = (raw or "").strip().replace("-", "").replace(".", "")[:8]
    if len(s) != 8 or not s.isdigit():
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None


def _items_from_json(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    header = (
        payload.get("response", {}).get("header")
        if isinstance(payload.get("response"), dict)
        else payload.get("header")
    )
    if isinstance(header, dict):
        code = str(header.get("resultCode") or "")
        msg = str(header.get("resultMsg") or "")
        if code and code not in {"00", "0", "NORMAL_SERVICE"}:
            raise RuntimeError(f"redev API resultCode={code} {msg}")
    for path in (
        ("response", "body", "items"),
        ("body", "items"),
        ("items",),
    ):
        cur: Any = payload
        ok = True
        for key in path:
            if not isinstance(cur, dict) or key not in cur:
                ok = False
                break
            cur = cur[key]
        if not ok:
            continue
        if isinstance(cur, list):
            return [x for x in cur if isinstance(x, dict)]
        if isinstance(cur, dict):
            if "item" in cur:
                item = cur["item"]
                if isinstance(item, list):
                    return [x for x in item if isinstance(x, dict)]
                if isinstance(item, dict):
                    return [item]
            return [cur]
    return []


def _items_from_xml(text: str) -> list[dict[str, Any]]:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return []
    # error payload
    for tag in ("resultCode", "resultMsg"):
        pass
    codes = [
        _text(el)
        for el in root.iter()
        if (el.tag.split("}")[-1] if "}" in el.tag else el.tag) == "resultCode"
    ]
    msgs = [
        _text(el)
        for el in root.iter()
        if (el.tag.split("}")[-1] if "}" in el.tag else el.tag) == "resultMsg"
    ]
    if codes and codes[0] not in {"00", "0", "NORMAL_SERVICE", ""}:
        raise RuntimeError(f"redev API resultCode={codes[0]} {msgs[0] if msgs else ''}")

    out: list[dict[str, Any]] = []
    for item in root.iter():
        tag = item.tag.split("}")[-1].lower() if "}" in item.tag else item.tag.lower()
        if tag != "item":
            continue
        row: dict[str, Any] = {}
        for child in list(item):
            ctag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
            row[ctag] = _text(child)
        if row:
            out.append(row)
    return out


def _row_to_fields(row: dict[str, Any]) -> dict[str, Any] | None:
    zone = _pick(row, "ZONE_NM", "zoneNm", "구역명")
    ctpv = _pick(row, "CTPV_NM", "ctpvNm", "시도명")
    sgg = _pick(row, "SGG_NM", "sggNm", "시군구명")
    sido = normalize_sido(ctpv)
    if not sido or not zone:
        return None
    progress = _pick(row, "PRGRS_STP_CN", "prgrsStpCn", "진행단계내용")
    hh = _pick(row, "HH_CNT", "hhCnt", "세대수")
    dsgn = _pick(row, "DSGN_YMD", "dsgnYmd", "지정일자")
    as_of = _pick(row, "DATA_CRTR_YMD", "dataCrtrYmd", "데이터기준일자")
    parts = []
    if progress:
        parts.append(f"진행단계: {progress}")
    if hh:
        parts.append(f"세대수 {hh}")
    if dsgn:
        parts.append(f"지정 {dsgn}")
    summary = " · ".join(parts)
    return {
        "zone": zone,
        "sido": sido,
        "sgg": sgg,
        "summary": summary,
        "data_as_of": _parse_ymd(as_of) or _parse_ymd(dsgn),
        "detail": {
            "ZONE_NM": zone,
            "CTPV_NM": ctpv,
            "SGG_NM": sgg,
            "PRGRS_STP_CN": progress,
            "HH_CNT": hh,
            "DSGN_YMD": dsgn,
            "DATA_CRTR_YMD": as_of,
        },
    }


def _norm_header(h: str) -> str:
    return re.sub(r"\s+", "", (h or "").strip().lower())


def _csv_row_to_fields(
    row: dict[str, str], *, default_sido: str, source_label: str
) -> dict[str, Any] | None:
    """지자체 CSV 컬럼 차이를 느슨하게 매핑."""
    # normalize keys
    mapped = {_norm_header(k): (v or "").strip() for k, v in row.items()}

    def get(*names: str) -> str:
        for n in names:
            v = mapped.get(_norm_header(n), "")
            if v:
                return v
        return ""

    zone = get(
        "구역명",
        "구 역 명",
        "구역 명",
        "정비구역명",
        "사업명",
        "사업장명",
        "지구명",
        "단지명",
        "아파트명",
    )
    if not zone:
        return None

    sgg = get("구명", "시군구명", "시군명", "구청", "행정구역", "자치구")
    loc = get("위치", "정비구역위치및면적(제곱미터)", "대지위치", "단지위치")
    # 부천: "정비구역위치 및 면적" 계열
    if not loc:
        for k, v in mapped.items():
            if "위치" in k and v:
                loc = v
                break

    progress = get("진행단계", "추진단계", "현황", "단계")
    biz = get("사업유형", "정비유형", "정비 유형", "구분", "사업방식")
    hh = get("세대수", "계획세대수", "조합원수")

    sido = default_sido
    # 위치/주소에 시도가 있으면 보정
    for blob in (loc, zone, sgg):
        n = normalize_sido(blob)
        if n:
            sido = n
            break

    if sido not in {"서울", "경기", "인천"}:
        return None

    parts = []
    if biz:
        parts.append(biz)
    if progress:
        parts.append(f"진행단계: {progress}")
    if hh:
        parts.append(f"세대수 {hh}")
    if loc:
        parts.append(loc[:80])
    summary = " · ".join(parts) if parts else source_label

    if not sgg and loc:
        # "중구 …" / "부천시 …" 앞토큰
        sgg = loc.split()[0][:32]

    return {
        "zone": zone[:200],
        "sido": sido,
        "sgg": sgg[:64],
        "summary": summary[:400],
        "data_as_of": None,
        "detail": {
            "source_label": source_label,
            "biz": biz,
            "progress": progress,
            "location": loc,
            "hh": hh,
        },
    }


def _decode_csv_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "cp949", "euc-kr", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def parse_csv_insights(
    text: str, *, default_sido: str, source_label: str
) -> list[dict[str, Any]]:
    if not text or text.lstrip().startswith("<!"):
        return []
    reader = csv.DictReader(io.StringIO(text))
    out: list[dict[str, Any]] = []
    for row in reader:
        if not isinstance(row, dict):
            continue
        fields = _csv_row_to_fields(
            {str(k): str(v or "") for k, v in row.items() if k is not None},
            default_sido=default_sido,
            source_label=source_label,
        )
        if fields:
            out.append(fields)
    return out


async def _resolve_csv_download_url(
    client: httpx.AsyncClient, page_id: str
) -> str | None:
    page = f"https://www.data.go.kr/data/{page_id}/fileData.do"
    res = await client.get(page)
    res.raise_for_status()
    m = re.search(
        r"/cmm/cmm/fileDownload\.do\?atchFileId=(FILE_[0-9]+)&fileDetailSn=(\d+)",
        res.text,
    )
    if not m:
        return None
    return (
        "https://www.data.go.kr/cmm/cmm/fileDownload.do"
        f"?atchFileId={m.group(1)}&fileDetailSn={m.group(2)}&insertDataPrcus=N"
    )


async def _fetch_page(
    client: httpx.AsyncClient,
    *,
    service_key: str,
    page_no: int,
    page_size: int,
) -> list[dict[str, Any]]:
    params = {
        "serviceKey": service_key,
        "pageNo": page_no,
        "numOfRows": page_size,
        "type": "json",
    }
    res = await client.get(REDEV_API_URL, params=params)
    res.raise_for_status()
    ctype = (res.headers.get("content-type") or "").lower()
    text = res.text
    if "json" in ctype or text.lstrip().startswith("{"):
        try:
            return _items_from_json(res.json())
        except RuntimeError:
            raise
        except Exception:  # noqa: BLE001
            return _items_from_xml(text)
    return _items_from_xml(text)


async def _upsert_fields(
    db: AsyncSession,
    fields: dict[str, Any],
    *,
    source: str,
    source_url: str,
    publisher: str,
) -> None:
    ext = external_id_hash(fields["sido"], fields["sgg"], fields["zone"], source)
    await upsert_insight(
        db,
        source=source,
        external_id=ext,
        category="재개발정비",
        sido=fields["sido"],
        sgg=fields["sgg"],
        title=fields["zone"],
        summary=fields["summary"],
        source_url=source_url,
        publisher=publisher,
        published_at=None,
        data_as_of=fields.get("data_as_of"),
        detail=fields.get("detail") or {},
    )


async def _ingest_openapi(
    db: AsyncSession,
    client: httpx.AsyncClient,
    *,
    service_key: str,
    max_pages: int,
    page_size: int,
) -> tuple[int, str]:
    upserted = 0
    pages = 0
    for page in range(1, max(1, max_pages) + 1):
        rows = await _fetch_page(
            client, service_key=service_key, page_no=page, page_size=page_size
        )
        pages += 1
        if not rows:
            break
        for row in rows:
            fields = _row_to_fields(row)
            if not fields:
                continue
            await _upsert_fields(
                db,
                fields,
                source="redev_std",
                source_url="https://www.data.go.kr/data/15155703/standard.do",
                publisher="국토교통부·지자체",
            )
            upserted += 1
        await db.commit()
        if len(rows) < page_size:
            break
        await asyncio.sleep(0.25)
    return upserted, f"openapi upserted={upserted} pages={pages}"


async def _ingest_csv_fallbacks(
    db: AsyncSession, client: httpx.AsyncClient
) -> tuple[int, str]:
    total = 0
    notes: list[str] = []
    for cfg in CSV_FALLBACK_PAGES:
        page_id = cfg["page_id"]
        try:
            dl = await _resolve_csv_download_url(client, page_id)
            if not dl:
                notes.append(f"{page_id}:no-dl")
                continue
            res = await client.get(dl)
            res.raise_for_status()
            text = _decode_csv_bytes(res.content)
            rows = parse_csv_insights(
                text, default_sido=cfg["sido"], source_label=cfg["label"]
            )
            n = 0
            for fields in rows:
                await _upsert_fields(
                    db,
                    fields,
                    source="redev_csv",
                    source_url=cfg["source_url"],
                    publisher=cfg["label"],
                )
                n += 1
            await db.commit()
            total += n
            notes.append(f"{page_id}:{n}")
            await asyncio.sleep(0.2)
        except Exception as exc:  # noqa: BLE001
            logger.warning("csv fallback %s failed: %s", page_id, exc)
            notes.append(f"{page_id}:err")
            await db.rollback()
    return total, "csv " + ",".join(notes)


async def ingest_redevelopment(
    db: AsyncSession,
    settings: Settings,
    *,
    max_pages: int = 20,
    page_size: int = 100,
) -> IngestRun:
    """기존 MOLIT 키 OpenAPI → 실패/0건이면 공개 CSV 폴백."""
    key = settings.redev_service_key
    upserted = 0
    parts: list[str] = []
    status = "ok"

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(45.0),
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        ) as client:
            if key:
                try:
                    n, msg = await _ingest_openapi(
                        db,
                        client,
                        service_key=key,
                        max_pages=max_pages,
                        page_size=page_size,
                    )
                    upserted += n
                    parts.append(msg)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("redev openapi failed, csv fallback: %s", exc)
                    parts.append(f"openapi_fail:{str(exc)[:120]}")
            else:
                parts.append("openapi_skipped:no_molit_key")

            if upserted == 0:
                n, msg = await _ingest_csv_fallbacks(db, client)
                upserted += n
                parts.append(msg)

        if upserted == 0:
            status = "empty"
        message = " | ".join(parts)
    except Exception as exc:  # noqa: BLE001
        logger.exception("redevelopment ingest failed")
        status = "error"
        message = f"redev failed: {str(exc)[:400]}"
        await db.rollback()

    run = IngestRun(
        source="redev",
        status=status,
        lot_count=upserted,
        message=message[:500],
        finished_at=datetime.utcnow(),
    )
    db.add(run)
    await db.commit()
    return run
