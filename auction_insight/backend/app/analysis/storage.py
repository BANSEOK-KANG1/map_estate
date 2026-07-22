"""Document storage abstraction — swap local disk for S3/R2 without rewriting callers."""

from __future__ import annotations

import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path


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
    """Dev/fallback only. Production should set ANALYSIS_DOC_STORE=s3."""

    def __init__(self, root: str | None = None):
        self.root = Path(root or os.getenv("ANALYSIS_DOC_ROOT", "./data/analysis_docs"))
        self.root.mkdir(parents=True, exist_ok=True)

    async def put(self, data: bytes, *, content_type: str, suffix: str = ".pdf") -> str:
        key = f"{uuid.uuid4().hex}{suffix}"
        (self.root / key).write_bytes(data)
        return key

    async def get(self, storage_key: str) -> bytes:
        return (self.root / storage_key).read_bytes()

    async def delete(self, storage_key: str) -> None:
        path = self.root / storage_key
        if path.exists():
            path.unlink()


class S3DocumentStore(DocumentStore):
    """Placeholder — wire boto3/aiobotocore when bucket credentials exist."""

    def __init__(self) -> None:
        self.bucket = os.getenv("ANALYSIS_S3_BUCKET", "")
        if not self.bucket:
            raise RuntimeError("ANALYSIS_S3_BUCKET required for s3 store")

    async def put(self, data: bytes, *, content_type: str, suffix: str = ".pdf") -> str:
        raise NotImplementedError(
            "S3DocumentStore.put: configure AWS credentials and implement with aiobotocore"
        )

    async def get(self, storage_key: str) -> bytes:
        raise NotImplementedError("S3DocumentStore.get not implemented yet")

    async def delete(self, storage_key: str) -> None:
        raise NotImplementedError("S3DocumentStore.delete not implemented yet")


def get_document_store() -> DocumentStore:
    kind = (os.getenv("ANALYSIS_DOC_STORE") or "local").lower()
    if kind == "s3":
        return S3DocumentStore()
    return LocalDocumentStore()
