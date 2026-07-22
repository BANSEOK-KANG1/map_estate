"""Tests for PDF classify + PII (no PDF binary required)."""

from app.analysis.pdf_extract import classify_document, excerpt_around
from app.analysis.pii import mask_pii


def test_classify_registry():
    t, conf, note = classify_document("본건 등기사항전부증명서 갑구 소유권 을구 근저당권", filename="등기.pdf")
    assert t == "registry"
    assert conf > 0


def test_classify_onbid():
    t, conf, _ = classify_document("캠코 온비드 공매공고 입찰보증금", filename="notice.pdf")
    assert t == "onbid_notice"


def test_excerpt_and_mask():
    text = "갑구 기재 홍길동 900101-1234567 연락 010-2222-3333 근저당"
    masked, did = mask_pii(text)
    assert did
    assert "1234567" not in masked
    ex = excerpt_around(masked, "근저당", radius=20)
    assert "근저당" in ex
