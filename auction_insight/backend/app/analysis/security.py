"""Upload / storage path hardening helpers."""

from __future__ import annotations

import re
from pathlib import Path

ALLOWED_SUFFIXES = {".pdf", ".txt"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
    "text/plain",
    "text/plain; charset=utf-8",
    "application/octet-stream",  # browsers sometimes send this for pdf
}

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._\-\uac00-\ud7a3]+")


def sanitize_filename(filename: str, *, default: str = "upload.pdf") -> str:
    name = (filename or default).strip().replace("\\", "/").split("/")[-1]
    name = _SAFE_NAME.sub("_", name).strip("._") or default
    return name[:200]


def detect_suffix(filename: str, content_type: str = "") -> str:
    lower = filename.lower()
    ct = (content_type or "").split(";")[0].strip().lower()
    if lower.endswith(".txt") or ct.startswith("text/"):
        return ".txt"
    return ".pdf"


def assert_upload_allowed(*, filename: str, content_type: str, data: bytes) -> None:
    if not data:
        raise ValueError("empty file")
    suffix = Path(filename).suffix.lower() or detect_suffix(filename, content_type)
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError("only PDF/TXT uploads are allowed")
    ct = (content_type or "").split(";")[0].strip().lower()
    if ct and ct not in ALLOWED_CONTENT_TYPES and not ct.startswith("text/"):
        # allow empty content-type from some clients
        if ct not in {"", "*/*"}:
            raise ValueError(f"unsupported content type: {ct}")
    # PDF magic when claimed pdf
    if suffix == ".pdf" and len(data) >= 5 and not data[:5].startswith(b"%PDF"):
        # still allow if content says octet-stream but reject clear non-pdf text bombs? soft check
        if data[:1] not in (b"%",) and b"%PDF" not in data[:1024]:
            raise ValueError("file does not look like a PDF")


def sanitize_storage_key(storage_key: str) -> str:
    key = (storage_key or "").strip().replace("\\", "/")
    if not key or key.startswith("/") or ".." in key.split("/"):
        raise ValueError("invalid storage key")
    # uuid-style only: hex + optional suffix
    base = Path(key).name
    if base != key:
        raise ValueError("invalid storage key path")
    if not re.fullmatch(r"[0-9a-fA-F]{16,64}\.(pdf|txt)", base):
        raise ValueError("invalid storage key format")
    return base


def safe_path(root: Path, storage_key: str) -> Path:
    key = sanitize_storage_key(storage_key)
    root_resolved = root.resolve()
    path = (root_resolved / key).resolve()
    if path.parent != root_resolved:
        raise ValueError("path escapes document root")
    return path
