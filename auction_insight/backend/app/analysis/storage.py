"""Document storage abstraction — local disk or S3-compatible (AWS/R2/MinIO)."""

from __future__ import annotations

import asyncio
import os
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.analysis.security import safe_path, sanitize_storage_key


class DocumentStore(ABC):
    @abstractmethod
    async def put(self, data: bytes, *, content_type: str, suffix: str = ".pdf") -> str:
        """Returns storage_key (opaque uuid + suffix)."""

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
        await asyncio.to_thread(path.write_bytes, data)
        return key

    async def get(self, storage_key: str) -> bytes:
        path = safe_path(self.root, storage_key)
        if not path.is_file():
            raise FileNotFoundError(storage_key)
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, storage_key: str) -> None:
        path = safe_path(self.root, storage_key)
        if path.exists():
            await asyncio.to_thread(path.unlink)


class MemoryDocumentStore(DocumentStore):
    """In-process store for unit tests."""

    def __init__(self) -> None:
        self._blobs: dict[str, tuple[bytes, str]] = {}

    async def put(self, data: bytes, *, content_type: str, suffix: str = ".pdf") -> str:
        if suffix not in (".pdf", ".txt"):
            suffix = ".pdf"
        key = f"{uuid.uuid4().hex}{suffix}"
        self._blobs[key] = (data, content_type)
        return key

    async def get(self, storage_key: str) -> bytes:
        key = sanitize_storage_key(storage_key)
        if key not in self._blobs:
            raise FileNotFoundError(key)
        return self._blobs[key][0]

    async def delete(self, storage_key: str) -> None:
        key = sanitize_storage_key(storage_key)
        self._blobs.pop(key, None)


class S3DocumentStore(DocumentStore):
    """S3-compatible object storage (AWS S3, Cloudflare R2, MinIO).

    Env:
      ANALYSIS_S3_BUCKET (required)
      ANALYSIS_S3_PREFIX (default analysis-docs)
      ANALYSIS_S3_REGION (default auto)
      ANALYSIS_S3_ENDPOINT_URL (R2/MinIO — optional)
      ANALYSIS_S3_ACCESS_KEY / ANALYSIS_S3_SECRET_KEY
        or AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
    """

    def __init__(self) -> None:
        self.bucket = os.getenv("ANALYSIS_S3_BUCKET", "").strip()
        self.prefix = (os.getenv("ANALYSIS_S3_PREFIX") or "analysis-docs").strip("/")
        self.region = (
            os.getenv("ANALYSIS_S3_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "auto"
        ).strip()
        self.endpoint_url = (os.getenv("ANALYSIS_S3_ENDPOINT_URL") or "").strip() or None
        self.access_key = (
            os.getenv("ANALYSIS_S3_ACCESS_KEY")
            or os.getenv("AWS_ACCESS_KEY_ID")
            or ""
        ).strip()
        self.secret_key = (
            os.getenv("ANALYSIS_S3_SECRET_KEY")
            or os.getenv("AWS_SECRET_ACCESS_KEY")
            or ""
        ).strip()
        if not self.bucket:
            raise RuntimeError("ANALYSIS_S3_BUCKET required for s3 store")
        if not self.access_key or not self.secret_key:
            raise RuntimeError(
                "ANALYSIS_S3_ACCESS_KEY/SECRET (or AWS_ACCESS_KEY_ID/SECRET) required"
            )
        self._client = None

    def _object_key(self, storage_key: str) -> str:
        key = sanitize_storage_key(storage_key)
        return f"{self.prefix}/{key}" if self.prefix else key

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            import boto3
            from botocore.config import Config
        except ImportError as e:
            raise RuntimeError(
                "boto3 is required for ANALYSIS_DOC_STORE=s3 — pip install boto3"
            ) from e
        kwargs: dict = {
            "service_name": "s3",
            "region_name": self.region if self.region != "auto" else "us-east-1",
            "aws_access_key_id": self.access_key,
            "aws_secret_access_key": self.secret_key,
            "config": Config(signature_version="s3v4"),
        }
        if self.endpoint_url:
            kwargs["endpoint_url"] = self.endpoint_url
        self._client = boto3.client(**kwargs)
        return self._client

    def _put_sync(self, key: str, data: bytes, content_type: str) -> None:
        client = self._get_client()
        client.put_object(
            Bucket=self.bucket,
            Key=self._object_key(key),
            Body=data,
            ContentType=content_type or "application/octet-stream",
        )

    def _get_sync(self, key: str) -> bytes:
        client = self._get_client()
        try:
            resp = client.get_object(Bucket=self.bucket, Key=self._object_key(key))
        except Exception as e:  # noqa: BLE001
            # Normalize missing object
            code = getattr(e, "response", {}).get("Error", {}).get("Code", "")
            if code in {"NoSuchKey", "404", "NotFound"} or "NoSuchKey" in str(e):
                raise FileNotFoundError(key) from e
            raise
        body = resp["Body"].read()
        return body

    def _delete_sync(self, key: str) -> None:
        client = self._get_client()
        client.delete_object(Bucket=self.bucket, Key=self._object_key(key))

    async def put(self, data: bytes, *, content_type: str, suffix: str = ".pdf") -> str:
        if suffix not in (".pdf", ".txt"):
            suffix = ".pdf"
        key = f"{uuid.uuid4().hex}{suffix}"
        await asyncio.to_thread(self._put_sync, key, data, content_type)
        return key

    async def get(self, storage_key: str) -> bytes:
        key = sanitize_storage_key(storage_key)
        return await asyncio.to_thread(self._get_sync, key)

    async def delete(self, storage_key: str) -> None:
        key = sanitize_storage_key(storage_key)
        await asyncio.to_thread(self._delete_sync, key)


def get_document_store() -> DocumentStore:
    kind = (os.getenv("ANALYSIS_DOC_STORE") or "local").lower()
    if kind in {"s3", "r2", "minio"}:
        return S3DocumentStore()
    if kind == "memory":
        return MemoryDocumentStore()
    return LocalDocumentStore()


def document_store_status() -> dict:
    kind = (os.getenv("ANALYSIS_DOC_STORE") or "local").lower()
    out: dict = {
        "kind": kind,
        "ready": True,
        "warning": None,
        "bucket": None,
        "endpoint_configured": bool(os.getenv("ANALYSIS_S3_ENDPOINT_URL")),
    }
    if kind == "local":
        out["warning"] = (
            "local DocumentStore is ephemeral on Render free disk — "
            "set ANALYSIS_DOC_STORE=s3 (or r2) + ANALYSIS_S3_BUCKET for persistence"
        )
    elif kind in {"s3", "r2", "minio"}:
        try:
            store = S3DocumentStore()
            out["bucket"] = store.bucket
            out["ready"] = True
            out["warning"] = None
            # Verify boto3 import without network call
            try:
                store._get_client()
            except RuntimeError as e:
                out["ready"] = False
                out["warning"] = str(e)
        except RuntimeError as e:
            out["ready"] = False
            out["warning"] = str(e)
    elif kind == "memory":
        out["warning"] = "memory store — test only, not durable"
    return out
