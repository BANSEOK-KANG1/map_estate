"""DocumentStore local/memory/s3-config tests."""

import asyncio
from pathlib import Path

import pytest

from app.analysis.storage import (
    LocalDocumentStore,
    MemoryDocumentStore,
    S3DocumentStore,
    document_store_status,
    get_document_store,
)


def test_memory_roundtrip():
    store = MemoryDocumentStore()

    async def _run():
        key = await store.put(b"hello", content_type="text/plain", suffix=".txt")
        assert key.endswith(".txt")
        assert await store.get(key) == b"hello"
        await store.delete(key)
        with pytest.raises(FileNotFoundError):
            await store.get(key)

    asyncio.run(_run())


def test_local_roundtrip(tmp_path: Path):
    store = LocalDocumentStore(root=str(tmp_path))

    async def _run():
        key = await store.put(
            b"%PDF-1.4 test", content_type="application/pdf", suffix=".pdf"
        )
        assert (tmp_path / key).is_file()
        assert await store.get(key) == b"%PDF-1.4 test"

    asyncio.run(_run())


def test_s3_requires_creds(monkeypatch):
    monkeypatch.setenv("ANALYSIS_S3_BUCKET", "my-bucket")
    monkeypatch.delenv("ANALYSIS_S3_ACCESS_KEY", raising=False)
    monkeypatch.delenv("ANALYSIS_S3_SECRET_KEY", raising=False)
    monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)
    with pytest.raises(RuntimeError, match="ACCESS"):
        S3DocumentStore()


def test_get_store_s3_kind(monkeypatch):
    monkeypatch.setenv("ANALYSIS_DOC_STORE", "s3")
    monkeypatch.setenv("ANALYSIS_S3_BUCKET", "b")
    monkeypatch.setenv("ANALYSIS_S3_ACCESS_KEY", "ak")
    monkeypatch.setenv("ANALYSIS_S3_SECRET_KEY", "sk")
    store = get_document_store()
    assert isinstance(store, S3DocumentStore)
    st = document_store_status()
    assert st["kind"] == "s3"
    assert st["bucket"] == "b"


def test_auth_write_detection(monkeypatch):
    from app.analysis.auth import analysis_api_key, is_analysis_write

    monkeypatch.setenv("ANALYSIS_API_KEY", "secret")
    assert analysis_api_key() == "secret"
    assert is_analysis_write("POST", "/api/analysis/items") is True
    assert is_analysis_write("GET", "/api/analysis/items") is False
    assert is_analysis_write("POST", "/api/analysis/money/validate") is False
