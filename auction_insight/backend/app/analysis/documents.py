"""Document upload, correction, evidence helpers."""

from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis.models import AuctionDocument, RightEntry
from app.analysis.pdf_extract import classify_document, excerpt_around, extract_pdf_pages
from app.analysis.pii import mask_pii
from app.analysis.service import get_item, recompute
from app.analysis.storage import get_document_store


async def upload_document(
    session: AsyncSession,
    item_id: int,
    *,
    filename: str,
    data: bytes,
    content_type: str = "application/pdf",
    doc_type_hint: str | None = None,
) -> AuctionDocument:
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    if not data:
        raise ValueError("empty file")
    if len(data) > 25 * 1024 * 1024:
        raise ValueError("file too large (max 25MB)")

    store = get_document_store()
    suffix = ".pdf"
    lower = filename.lower()
    if lower.endswith(".txt"):
        suffix = ".txt"
    storage_key = await store.put(data, content_type=content_type or "application/pdf", suffix=suffix)

    if suffix == ".txt" or content_type.startswith("text/"):
        text = data.decode("utf-8", errors="replace")
        text, masked = mask_pii(text)
        pages = [{"page": 1, "text": text[:8000], "char_count": min(len(text), 8000)}]
        page_count = 1
        full = text[:200_000]
        doc_type, conf, note = classify_document(full, filename=filename)
        any_masked = masked
    else:
        extracted = extract_pdf_pages(data)
        pages = extracted.pages
        page_count = extracted.page_count
        full = extracted.full_text
        doc_type, conf, note = extracted.doc_type, extracted.confidence, extracted.classify_note
        any_masked = extracted.masked

    if doc_type_hint and doc_type_hint in {
        "registry",
        "appraisal",
        "sale_spec",
        "onbid_notice",
        "other",
    }:
        note = f"사용자 힌트={doc_type_hint}; 자동={doc_type} ({note})"
        doc_type = doc_type_hint
        conf = max(conf, 0.9)

    doc = AuctionDocument(
        item_id=item_id,
        doc_type=doc_type,
        filename=filename[:250],
        storage_key=storage_key,
        content_type=content_type or "application/pdf",
        page_count=page_count,
        extracted_text=full,
        pages_json=json.dumps(pages, ensure_ascii=False),
        classify_confidence=conf,
        classify_note=note,
        masked=1 if any_masked else 0,
        confirmed_at=None,
        user_corrected=0,
    )
    session.add(doc)
    await session.commit()
    await session.refresh(doc)
    await recompute(session, item_id)
    return doc


async def get_document(session: AsyncSession, doc_id: int) -> AuctionDocument | None:
    return await session.get(AuctionDocument, doc_id)


def serialize_document(doc: AuctionDocument, *, include_pages: bool = True) -> dict:
    pages = []
    try:
        pages = json.loads(doc.pages_json or "[]")
    except json.JSONDecodeError:
        pages = []
    out = {
        "id": doc.id,
        "item_id": doc.item_id,
        "doc_type": doc.doc_type,
        "filename": doc.filename,
        "storage_key": doc.storage_key,
        "content_type": doc.content_type,
        "page_count": doc.page_count,
        "masked": bool(doc.masked),
        "classify_confidence": doc.classify_confidence,
        "classify_note": doc.classify_note,
        "user_corrected": bool(doc.user_corrected),
        "confirmed_at": doc.confirmed_at.isoformat() if doc.confirmed_at else None,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "text_preview": (doc.extracted_text or "")[:500],
    }
    if include_pages:
        # Cap page text in list responses
        slim = []
        for p in pages[:40]:
            if not isinstance(p, dict):
                continue
            text = str(p.get("text") or "")
            slim.append(
                {
                    "page": p.get("page"),
                    "char_count": p.get("char_count") or len(text),
                    "text_preview": text[:400],
                }
            )
        out["pages"] = slim
    return out


async def correct_document(
    session: AsyncSession,
    doc_id: int,
    *,
    doc_type: str | None = None,
    extracted_text: str | None = None,
    confirm: bool = False,
) -> AuctionDocument:
    doc = await get_document(session, doc_id)
    if doc is None:
        raise LookupError("document not found")
    if doc_type:
        if doc_type not in {"registry", "appraisal", "sale_spec", "onbid_notice", "other"}:
            raise ValueError("invalid doc_type")
        doc.doc_type = doc_type
        doc.classify_note = (doc.classify_note or "") + " | 사용자 유형 교정"
        doc.classify_confidence = 1.0
    if extracted_text is not None:
        masked, did = mask_pii(extracted_text)
        doc.extracted_text = masked[:200_000]
        if did:
            doc.masked = 1
        # refresh page 1 preview if single-page override
        try:
            pages = json.loads(doc.pages_json or "[]")
        except json.JSONDecodeError:
            pages = []
        if pages and isinstance(pages[0], dict):
            pages[0]["text"] = masked[:8000]
            pages[0]["char_count"] = min(len(masked), 8000)
            doc.pages_json = json.dumps(pages, ensure_ascii=False)
        else:
            doc.pages_json = json.dumps(
                [{"page": 1, "text": masked[:8000], "char_count": min(len(masked), 8000)}],
                ensure_ascii=False,
            )
    doc.user_corrected = 1
    if confirm:
        doc.confirmed_at = datetime.utcnow()
    await session.commit()
    await session.refresh(doc)
    await recompute(session, doc.item_id)
    return doc


async def page_evidence(
    session: AsyncSession,
    doc_id: int,
    page: int,
    *,
    query: str = "",
) -> dict:
    doc = await get_document(session, doc_id)
    if doc is None:
        raise LookupError("document not found")
    try:
        pages = json.loads(doc.pages_json or "[]")
    except json.JSONDecodeError:
        pages = []
    hit = next((p for p in pages if isinstance(p, dict) and int(p.get("page") or 0) == page), None)
    if hit is None:
        raise LookupError(f"page {page} not found")
    text = str(hit.get("text") or "")
    excerpt = excerpt_around(text, query)
    return {
        "doc_id": doc.id,
        "doc_type": doc.doc_type,
        "filename": doc.filename,
        "page": page,
        "excerpt": excerpt,
        "confirmed_at": doc.confirmed_at.isoformat() if doc.confirmed_at else None,
        "note": "권리 확정 시 이 발췌·페이지·문서ID를 RightEntry에 연결하세요.",
    }


async def attach_evidence_as_right(
    session: AsyncSession,
    item_id: int,
    *,
    doc_id: int,
    page: int,
    label: str,
    kind: str = "other",
    query: str = "",
    amount_won: int | None = None,
) -> RightEntry:
    """Create a RightEntry in HOLD/UNKNOWN with mandatory evidence fields."""
    item = await get_item(session, item_id)
    if item is None:
        raise LookupError("item not found")
    ev = await page_evidence(session, doc_id, page, query=query)
    # Without confirmed doc, status stays HOLD
    doc = await get_document(session, doc_id)
    status = "HOLD" if doc and not doc.confirmed_at else "INFO"
    if doc is None or not (doc.extracted_text or "").strip():
        status = "UNKNOWN"
    rule_track = "court_malso" if item.source == "court" else "onbid_tax_distribute"
    entry = RightEntry(
        item_id=item_id,
        kind=kind or "other",
        label=label or f"{ev['doc_type']} p.{page}",
        amount_won=amount_won,
        status=status,
        evidence_doc_id=doc_id,
        evidence_page=page,
        evidence_excerpt=ev["excerpt"][:2000],
        confirmed_at=None,
        rule_track=rule_track,
        notes="문서 근거 연결됨. 선후순위·말소/인수는 결정론적 규칙 Phase 3에서 확정.",
    )
    session.add(entry)
    await session.commit()
    await session.refresh(entry)
    await recompute(session, item_id)
    return entry
