"""Deterministic rights / occupancy timeline evaluation.

Court (court_malso) and Onbid (onbid_tax_distribute) tracks are separate.
This module never decides bids — it only proposes EXTINGUISH/ASSUME/HOLD
when evidence + dates exist. Missing docs → UNKNOWN/HOLD only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


SAFE_WITHOUT_DOCS = frozenset({"UNKNOWN", "HOLD", "INFO"})
RIGHT_KINDS = frozenset({"mortgage", "seize", "lease_reg", "tax", "other", "baseline"})
OCC_KINDS = frozenset({"housing", "commercial"})


@dataclass
class TimelineEvent:
    sort_key: date | None
    kind: str  # right | occupancy | baseline
    label: str
    status: str
    amount_won: int | None
    track: str
    ref_id: int | None
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "date": self.sort_key.isoformat() if self.sort_key else None,
            "kind": self.kind,
            "label": self.label,
            "status": self.status,
            "amount_won": self.amount_won,
            "track": self.track,
            "ref_id": self.ref_id,
            "note": self.note,
        }


def _parse_date(v: date | datetime | str | None) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v).strip()[:10]
    try:
        return date.fromisoformat(s)
    except ValueError:
        return None


def pick_malso_baseline(rights: list[Any]) -> Any | None:
    """User-marked baseline first; else earliest mortgage/seize with a date."""
    marked = [r for r in rights if getattr(r, "is_malso_baseline", 0)]
    if marked:
        return marked[0]
    candidates = [
        r
        for r in rights
        if getattr(r, "kind", "") in ("mortgage", "seize", "baseline")
        and _parse_date(getattr(r, "event_date", None))
    ]
    if not candidates:
        return None
    return sorted(
        candidates,
        key=lambda r: (
            getattr(r, "priority_hint", None) is None,
            getattr(r, "priority_hint", 10**9) or 10**9,
            _parse_date(r.event_date) or date.max,
            r.id or 0,
        ),
    )[0]


def evaluate_court_right(
    right: Any,
    *,
    malso_date: date | None,
    is_baseline: bool,
    docs_ok: bool,
    has_evidence: bool,
) -> tuple[str, str]:
    """Returns (status, note). Court 말소기준: 이후 권리 → EXTINGUISH, 이전 → ASSUME 검토."""
    if not docs_ok or not has_evidence:
        return "HOLD", "필수문서·원문 근거 부족 — 법원 말소/인수 확정 금지"
    if is_baseline:
        return "INFO", "말소기준권리(사용자 지정 또는 추정). 법률 확정이 아닙니다."
    ed = _parse_date(getattr(right, "event_date", None))
    if malso_date is None or ed is None:
        return "HOLD", "말소기준일 또는 등기일이 없어 선후순위 판정 보류"
    if ed > malso_date:
        return (
            "EXTINGUISH",
            f"등기일 {ed} > 말소기준일 {malso_date} — 원칙상 말소(소멸) 후보. 원문·법률 재확인.",
        )
    if ed < malso_date:
        return (
            "ASSUME",
            f"등기일 {ed} < 말소기준일 {malso_date} — 선순위 인수 검토 후보. 배당·특약 확인.",
        )
    return "HOLD", "말소기준일과 동일 — 수동 확인 필요"


def evaluate_onbid_right(
    right: Any,
    *,
    docs_ok: bool,
    has_evidence: bool,
) -> tuple[str, str]:
    """Onbid: do NOT apply court malso extinguish. Tax/distribute track."""
    if not docs_ok or not has_evidence:
        return "HOLD", "온비드 원문·특약 근거 부족 — 조세/배분 확정 금지"
    kind = getattr(right, "kind", "") or ""
    ed = _parse_date(getattr(right, "event_date", None))
    if kind == "tax":
        if ed is None:
            return "HOLD", "조세 법정기일 미입력 — 배분요구·체납원문 확인 전 확정 금지"
        return (
            "INFO",
            f"조세 관련 일자 {ed} 기록됨. 법원 말소기준과 별도 — 배분·법정기일 원문으로 확인.",
        )
    # Non-tax registry-like items on onbid: informational relative order only
    if ed is None:
        return "HOLD", "일자 없음 — 온비드 등기·우선변제 목록과 대조하세요"
    return (
        "INFO",
        f"온비드 트랙 권리(일자 {ed}). 말소기준 자동소멸 로직 미적용 — 공고·배분 원문 확인.",
    )


def evaluate_occupancy(
    claim: Any,
    *,
    source: str,
    malso_date: date | None,
    docs_ok: bool,
) -> tuple[str, str]:
    has_ev = bool(getattr(claim, "evidence_doc_id", None))
    if not docs_ok or not has_ev:
        return "HOLD", "문서 근거 없는 점유·임차 주장 — 대항력 확정 금지"

    kind = getattr(claim, "claim_kind", "housing") or "housing"
    if kind == "housing":
        move_in = _parse_date(getattr(claim, "move_in_date", None))
        fixed = _parse_date(getattr(claim, "fixed_date", None))
        if move_in is None or fixed is None:
            return "HOLD", "주택: 전입일·확정일자 모두 필요 — 입력 후 재평가"
        if source == "court":
            if malso_date is None:
                return "HOLD", "말소기준일 미정 — 주택 대항력 비교 보류"
            if move_in <= malso_date and fixed <= malso_date:
                return (
                    "ASSUME",
                    f"전입 {move_in}·확정 {fixed} ≤ 말소기준 {malso_date} — 대항력 가능(인수 검토). 법률자문 아님.",
                )
            return (
                "HOLD",
                f"전입/확정일자가 말소기준 {malso_date} 이후 — 대항력 약화·배당·명도 리스크 확인",
            )
        # onbid: compare to claim dates only; no court malso
        return (
            "INFO",
            f"온비드 주택 임차 입력(전입 {move_in}, 확정 {fixed}). 공고 임대차·점유 목록과 대조.",
        )

    # commercial
    biz = _parse_date(getattr(claim, "business_reg_date", None))
    tax_ok = getattr(claim, "tax_invoice_ok", None)
    if biz is None:
        return "HOLD", "상가: 사업자등록일 필요 — 상가건물임대차보호법 요건 확인"
    if tax_ok is None:
        return "HOLD", "상가: 세금계산서 등 요건 입력 필요"
    if source == "court" and malso_date is not None:
        if biz <= malso_date and int(tax_ok) == 1:
            return (
                "ASSUME",
                f"사업자등록 {biz} ≤ 말소기준 {malso_date} · 세금계산서 OK — 상가 대항력 가능 후보",
            )
        return "HOLD", "상가 대항력 요건 불충분 또는 후순위 — 계약·원문 재확인"
    return (
        "INFO",
        f"온비드 상가 임차(사업자등록 {biz}, 세금계산서={'OK' if int(tax_ok or 0) else '미확인'}).",
    )


def apply_evaluation(
    item: Any,
    *,
    docs_ok: bool,
    persist: bool = True,
) -> dict[str, Any]:
    """Mutate rights/occupancies statuses; return timeline + summary."""
    rights = list(getattr(item, "rights", []) or [])
    occs = list(getattr(item, "occupancies", []) or [])
    source = getattr(item, "source", "court") or "court"
    track_default = "court_malso" if source == "court" else "onbid_tax_distribute"
    computed_right_status: dict[int, tuple[str, str]] = {}
    computed_occ_status: dict[int, tuple[str, str]] = {}

    baseline = pick_malso_baseline(rights) if source == "court" else None
    malso_date = _parse_date(getattr(baseline, "event_date", None)) if baseline else None

    notes_out: list[str] = []
    if source == "court":
        if baseline is None:
            notes_out.append("말소기준권리를 지정하거나 근저당/가압류 등기일을 입력하세요.")
        else:
            notes_out.append(
                f"말소기준 후보: {getattr(baseline, 'label', '')} "
                f"({malso_date or '일자없음'}) — 자동추정일 수 있음."
            )
    else:
        notes_out.append("온비드 트랙: 법원 말소기준 자동소멸 로직을 적용하지 않습니다.")

    for r in rights:
        has_ev = bool(
            getattr(r, "evidence_doc_id", None)
            and (getattr(r, "evidence_excerpt", "") or "").strip()
        )
        track = getattr(r, "rule_track", None) or track_default
        if persist and not getattr(r, "rule_track", None):
            r.rule_track = track_default
        is_base = baseline is not None and r is baseline
        if source == "court" and track != "onbid_tax_distribute":
            status, note = evaluate_court_right(
                r,
                malso_date=malso_date,
                is_baseline=is_base,
                docs_ok=docs_ok,
                has_evidence=has_ev,
            )
        else:
            status, note = evaluate_onbid_right(r, docs_ok=docs_ok, has_evidence=has_ev)
        computed_right_status[id(r)] = (status, note)
        if persist:
            r.status = status
            base_notes = (r.notes or "").split(" | [평가]")[0].strip()
            r.notes = f"{base_notes} | [평가] {note}".strip(" |")
            if is_base:
                r.is_malso_baseline = 1

    assume_deposit = 0
    for c in occs:
        status, note = evaluate_occupancy(
            c, source=source, malso_date=malso_date, docs_ok=docs_ok
        )
        computed_occ_status[id(c)] = (status, note)
        if persist:
            c.status = status
            base_notes = (c.notes or "").split(" | [평가]")[0].strip()
            c.notes = f"{base_notes} | [평가] {note}".strip(" |")
        if status == "ASSUME" and getattr(c, "deposit_won", None):
            assume_deposit += int(c.deposit_won or 0)

    assume_other = 0
    for r in rights:
        st = computed_right_status.get(id(r), (getattr(r, "status", ""), ""))[0]
        if st == "ASSUME" and getattr(r, "amount_won", None):
            assume_other += int(r.amount_won or 0)

    # Build timeline from computed statuses (even if not persisted)
    events: list[TimelineEvent] = []
    for r in rights:
        st, note = computed_right_status[id(r)]
        ed = _parse_date(getattr(r, "event_date", None))
        events.append(
            TimelineEvent(
                sort_key=ed,
                kind="baseline" if baseline is not None and r is baseline else "right",
                label=getattr(r, "label", "") or getattr(r, "kind", "right"),
                status=st,
                amount_won=getattr(r, "amount_won", None),
                track=getattr(r, "rule_track", "") or track_default,
                ref_id=getattr(r, "id", None),
                note=note,
            )
        )
    for c in occs:
        st, note = computed_occ_status[id(c)]
        ed = (
            _parse_date(getattr(c, "fixed_date", None))
            or _parse_date(getattr(c, "business_reg_date", None))
            or _parse_date(getattr(c, "move_in_date", None))
        )
        events.append(
            TimelineEvent(
                sort_key=ed,
                kind="occupancy",
                label=f"{getattr(c, 'claim_kind', '')}:{getattr(c, 'occupant_label', '') or '점유'}",
                status=st,
                amount_won=getattr(c, "deposit_won", None),
                track=track_default,
                ref_id=getattr(c, "id", None),
                note=note,
            )
        )

    def _key(e: TimelineEvent) -> tuple:
        return (e.sort_key is None, e.sort_key or date.max, e.kind, e.ref_id or 0)

    timeline = sorted(events, key=_key)
    risk_flags: list[str] = []
    if any(computed_right_status[id(r)][0] == "ASSUME" for r in rights):
        risk_flags.append("선순위_인수_후보")
    if any(computed_occ_status[id(c)][0] == "ASSUME" for c in occs):
        risk_flags.append("대항력_임차_인수_후보")
    if any(computed_right_status[id(r)][0] == "HOLD" for r in rights) or any(
        computed_occ_status[id(c)][0] == "HOLD" for c in occs
    ):
        risk_flags.append("미확정_HOLD")
    if not docs_ok:
        risk_flags.append("필수문서_결여")

    return {
        "track": track_default,
        "malso_baseline_id": getattr(baseline, "id", None) if baseline else None,
        "malso_date": malso_date.isoformat() if malso_date else None,
        "timeline": [e.as_dict() for e in timeline],
        "suggested_assume_deposit_won": assume_deposit,
        "suggested_assume_other_rights_won": assume_other,
        "risk_flags": risk_flags,
        "notes": notes_out,
        "disclaimer": "법률·세무 자문이 아닙니다. AI/자동평가는 입찰을 결정하지 않습니다.",
    }


def build_timeline(
    rights: list[Any],
    occs: list[Any],
    *,
    baseline: Any | None = None,
    track: str = "",
) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    for r in rights:
        ed = _parse_date(getattr(r, "event_date", None))
        events.append(
            TimelineEvent(
                sort_key=ed,
                kind="baseline" if baseline is not None and r is baseline else "right",
                label=getattr(r, "label", "") or getattr(r, "kind", "right"),
                status=getattr(r, "status", "UNKNOWN") or "UNKNOWN",
                amount_won=getattr(r, "amount_won", None),
                track=getattr(r, "rule_track", "") or track,
                ref_id=getattr(r, "id", None),
                note=(getattr(r, "notes", "") or "")[-180:],
            )
        )
    for c in occs:
        # prefer fixed_date / business_reg / move_in for sort
        ed = (
            _parse_date(getattr(c, "fixed_date", None))
            or _parse_date(getattr(c, "business_reg_date", None))
            or _parse_date(getattr(c, "move_in_date", None))
        )
        events.append(
            TimelineEvent(
                sort_key=ed,
                kind="occupancy",
                label=f"{getattr(c, 'claim_kind', '')}:{getattr(c, 'occupant_label', '') or '점유'}",
                status=getattr(c, "status", "UNKNOWN") or "UNKNOWN",
                amount_won=getattr(c, "deposit_won", None),
                track=track,
                ref_id=getattr(c, "id", None),
                note=(getattr(c, "notes", "") or "")[-180:],
            )
        )

    def _key(e: TimelineEvent) -> tuple:
        return (e.sort_key is None, e.sort_key or date.max, e.kind, e.ref_id or 0)

    return sorted(events, key=_key)
