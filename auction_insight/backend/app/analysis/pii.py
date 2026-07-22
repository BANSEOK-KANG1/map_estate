"""PII masking before persist."""

from __future__ import annotations

import re

_RRN = re.compile(r"\b(\d{6})[-\s]?(\d{7})\b")
_PHONE = re.compile(r"\b(01[016789])[-\s]?(\d{3,4})[-\s]?(\d{4})\b")


def mask_pii(text: str) -> tuple[str, bool]:
    if not text:
        return "", False
    masked = False

    def _rrn(m: re.Match[str]) -> str:
        nonlocal masked
        masked = True
        return f"{m.group(1)}-*******"

    def _phone(m: re.Match[str]) -> str:
        nonlocal masked
        masked = True
        return f"{m.group(1)}-****-{m.group(3)}"

    out = _RRN.sub(_rrn, text)
    out = _PHONE.sub(_phone, out)
    return out, masked
