"""PDF text extract + deterministic document type classification (no LLM)."""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from app.analysis.pii import mask_pii

# Keyword scores for doc_type classification (court vs onbid share some labels).
_CLASSIFY_RULES: list[tuple[str, list[str]]] = [
    (
        "registry",
        ["등기사항전부증명서", "등기부등본", "갑구", "을구", "근저당권", "가압류", "소유권"],
    ),
    (
        "appraisal",
        ["감정평가서", "감정평가액", "평가금액", "시가", "물건개요", "감정평가법인"],
    ),
    (
        "sale_spec",
        ["매각물건명세서", "매각기일", "최저매각가격", "일괄매각", "배당요구"],
    ),
    (
        "onbid_notice",
        ["온비드", "공매공고", "입찰보증금", "캠코", "한국자산관리공사", "공매예정가격"],
    ),
]


@dataclass
class ExtractResult:
    page_count: int
    pages: list[dict]  # {page, text, char_count}
    full_text: str
    masked: bool
    doc_type: str
    confidence: float
    classify_note: str


def extract_pdf_pages(data: bytes, *, max_pages: int = 80, max_chars_per_page: int = 8000) -> ExtractResult:
    """Extract text per page; mask PII before returning/storing."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("pypdf is required for PDF extraction") from e

    reader = PdfReader(io.BytesIO(data))
    pages: list[dict] = []
    any_masked = False
    n = min(len(reader.pages), max_pages)
    for i in range(n):
        raw = reader.pages[i].extract_text() or ""
        raw = raw.strip()
        if len(raw) > max_chars_per_page:
            raw = raw[:max_chars_per_page] + "\n…(truncated)"
        masked_text, did = mask_pii(raw)
        any_masked = any_masked or did
        pages.append(
            {
                "page": i + 1,
                "text": masked_text,
                "char_count": len(masked_text),
            }
        )
    full = "\n\n".join(f"[p.{p['page']}]\n{p['text']}" for p in pages if p["text"])
    full, did2 = mask_pii(full)
    any_masked = any_masked or did2
    doc_type, conf, note = classify_document(full, filename="")
    return ExtractResult(
        page_count=len(reader.pages),
        pages=pages,
        full_text=full[:200_000],
        masked=any_masked,
        doc_type=doc_type,
        confidence=conf,
        classify_note=note,
    )


def classify_document(text: str, *, filename: str = "") -> tuple[str, float, str]:
    """Deterministic keyword classifier. Returns (doc_type, confidence 0..1, note)."""
    blob = f"{filename}\n{text}".lower()
    # Keep original for Korean keywords
    blob_kr = f"{filename}\n{text}"
    scores: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for doc_type, kws in _CLASSIFY_RULES:
        for kw in kws:
            if kw.lower() in blob or kw in blob_kr:
                scores[doc_type] = scores.get(doc_type, 0) + 1
                hits.setdefault(doc_type, []).append(kw)
    if not scores:
        # filename hints
        fn = filename.lower()
        if "등기" in filename or "registry" in fn:
            return "registry", 0.4, "파일명 힌트(등기)"
        if "감정" in filename or "appraisal" in fn:
            return "appraisal", 0.4, "파일명 힌트(감정)"
        if "명세서" in filename or "sale" in fn:
            return "sale_spec", 0.4, "파일명 힌트(명세서)"
        if "온비드" in filename or "onbid" in fn or "공고" in filename:
            return "onbid_notice", 0.4, "파일명 힌트(공고)"
        return "other", 0.0, "키워드 없음 — 사용자가 유형을 교정하세요"
    best = max(scores, key=scores.get)
    total = sum(scores.values())
    conf = scores[best] / max(total, 1)
    note = f"키워드 {', '.join(hits[best][:4])}"
    if conf < 0.5:
        note += " (확신 낮음 — 교정 권장)"
    return best, round(conf, 2), note


def excerpt_around(page_text: str, query: str, *, radius: int = 120) -> str:
    if not page_text:
        return ""
    if not query:
        return page_text[: radius * 2]
    idx = page_text.find(query)
    if idx < 0:
        # loose: first line
        return page_text[: radius * 2]
    start = max(0, idx - radius)
    end = min(len(page_text), idx + len(query) + radius)
    chunk = page_text[start:end]
    if start > 0:
        chunk = "…" + chunk
    if end < len(page_text):
        chunk = chunk + "…"
    masked, _ = mask_pii(chunk)
    return masked


_DATE_RE = re.compile(r"(20\d{2})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})")


def find_dates(text: str) -> list[str]:
    out = []
    for m in _DATE_RE.finditer(text or ""):
        out.append(f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}")
    return out[:20]
