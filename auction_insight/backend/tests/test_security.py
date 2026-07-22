"""Phase 6 security helpers."""

from pathlib import Path

import pytest

from app.analysis.security import (
    assert_upload_allowed,
    safe_path,
    sanitize_filename,
    sanitize_storage_key,
)


def test_sanitize_filename_strips_path():
    assert ".." not in sanitize_filename("../../etc/passwd.pdf")
    assert sanitize_filename("foo/bar.pdf").endswith(".pdf")


def test_storage_key_rejects_traversal():
    with pytest.raises(ValueError):
        sanitize_storage_key("../secret.pdf")
    with pytest.raises(ValueError):
        sanitize_storage_key("a/b.pdf")
    key = "a" * 32 + ".pdf"
    assert sanitize_storage_key(key) == key


def test_safe_path_stays_in_root(tmp_path: Path):
    key = "b" * 32 + ".txt"
    (tmp_path / key).write_text("ok", encoding="utf-8")
    p = safe_path(tmp_path, key)
    assert p.parent == tmp_path.resolve()
    with pytest.raises(ValueError):
        safe_path(tmp_path, "../x.pdf")


def test_upload_rejects_bad_pdf_magic():
    with pytest.raises(ValueError):
        assert_upload_allowed(
            filename="x.pdf",
            content_type="application/pdf",
            data=b"not a pdf payload",
        )
    assert_upload_allowed(
        filename="ok.txt",
        content_type="text/plain",
        data="주민 900101-1234567".encode("utf-8"),
    )
