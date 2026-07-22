"""Document storage abstraction — swap local disk for S3/R2 without rewriting callers."""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.analysis.security import safe_path, sanitize_storage_key


class DocumentStore(ABC):
    @abstractmethod
    async def put(self, data: bytes, *, content_type: str, suffix: str = ".pdf") -> str:
        """Returns storage_key."""

    @abstractmethod
    async def get(self, storage_key: str) -> bytes:
        ...

    @abstractmethod
    async def delete(self, storage_key: str) -> None:
        ...


class LocalDocumentStore(DocumentStore):
    """Dev/fallback. Production: set ANALYSIS_DOC_STORE=s3 (+ bucket creds)."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or os.getenv("ANALYSIS_DOC_ROOT", "./data/analysis_docs"))
        self.root.mkdir(parents=True, exist_ok=True)

    async def put(self, data: bytes, *, content_type: str, suffix: str = ".pdf") -> str:
        if suffix not in (".pdf", ".txt"):
            suffix = ".pdf"
        key = f"{uuid.uuid4().hex}{suffix}"
        path = safe_path(self.root, key)
        path.write_bytes(data)
        return key

    async def get(self, storage_key: str) -> bytes:
        path = safe_path(self.root, storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return path.read_bytes()

    async def delete(self, storage_key: str) -> None:
        path = safe_path(self.root, storage_key)
        if path.exists():
            path.unlink()


class S3DocumentStore(DocumentStore):
    """Stub until AWS/R2 credentials are wired. Keys remain portable."""

    def __init__(self) -> None:
        self.bucket = os.getenv("ANALYSIS_S3_BUCKET", "")
        self.prefix = (os.getenv("ANALYSIS_S3_PREFIX") or "analysis-docs").strip("/")
        if not self.bucket:
            raise RuntimeError("ANALYSIS_S3_BUCKET required for s3 store")

    def _object_key(self, storage_key: str) -> str:
        key = sanitize_storage_key(storage_key)
        return f"{self.prefix}/{key}" if self.prefix else key

    async def put(self, data: bytes, *, content_type: str, suffix: str = ".pdf") -> str:
        raise NotImplementedError(
            "S3DocumentStore.put: install aiobotocore and set AWS credentials — "
            f"bucket={self.bucket}"
        )

    async def get(self, storage_key: str) -> bytes:
        _ = self._object_key(storage_key)
        raise NotImplementedError("S3DocumentStore.get not implemented yet")

    async def delete(self, storage_key: str) -> None:
        _ = self._object_key(storage_key)
        raise NotImplementedError("S3DocumentStore.delete not implemented yet")


def get_document_store() -> DocumentStore:
    kind = (os.getenv("ANALYSIS_DOC_STORE") or "local").lower()
    if kind == "s3":
        return S3DocumentStore()
    return LocalDocumentStore()


def document_store_status() -> dict:
    kind = (os.getenv("ANALYSIS_DOC_STORE") or "local").lower()
    out = {
        "kind": kind,
        "ready": True,
        "warning": None,
    }
    if kind == "local":
        out["warning"] = (
            "local DocumentStore is ephemeral on Render free disk — "
            "set ANALYSIS_DOC_STORE=s3 and ANALYSIS_S3_BUCKET for production persistence"
        )
    elif kind == "s3":
        try:
            S3DocumentStore()
            out["ready"] = False
            out["warning"] = "S3 store configured but put/get not implemented yet"
        except RuntimeError as e:
            out["ready"] = False
            out["warning"] = str(e)
    return out
