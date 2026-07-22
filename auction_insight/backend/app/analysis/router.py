from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analysis import documents as doc_service
from app.analysis import rights_service
from app.analysis import service
from app.analysis.models import RuleConfig
from app.analysis.money import detect_digit_errors, parse_user_amount, triple_dict
from app.analysis.rules import seed_rules
from app.analysis.schemas import (
    AuctionItemCreate,
    DocumentCorrectIn,
    EvidenceIn,
    FinanceUpdate,
    MoneyValidateIn,
    MoneyValidateOut,
    OccupancyCreateIn,
    OccupancyPatchIn,
    RightCreateIn,
    RightFromEvidenceIn,
    RightPatchIn,
    RuleOut,
    TimelineEvaluateIn,
)
from app.db import get_db

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.post("/money/validate", response_model=MoneyValidateOut)
async def validate_money(body: MoneyValidateIn) -> MoneyValidateOut:
    appraisal = body.appraisal_won
    if appraisal is None and body.appraisal_manwon is not None:
        appraisal = parse_user_amount(raw=body.appraisal_manwon, unit="manwon")
    min_bid = body.min_bid_won
    if min_bid is None and body.min_bid_manwon is not None:
        min_bid = parse_user_amount(raw=body.min_bid_manwon, unit="manwon")
    planned = body.planned_price_won
    if planned is None and body.planned_price_manwon is not None:
        planned = parse_user_amount(raw=body.planned_price_manwon, unit="manwon")
    warnings = detect_digit_errors(
        appraisal_won=appraisal,
        min_bid_won=min_bid,
        planned_price_won=planned,
    )
    return MoneyValidateOut(
        appraisal=triple_dict(appraisal),  # type: ignore[arg-type]
        min_bid=triple_dict(min_bid),  # type: ignore[arg-type]
        planned_price=triple_dict(planned),  # type: ignore[arg-type]
        warnings=warnings,
    )


@router.post("/items")
async def create_item(body: AuctionItemCreate, db: AsyncSession = Depends(get_db)):
    try:
        item = await service.create_item(db, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return service.serialize_detail(item)


@router.get("/items")
async def list_items(
    source: str | None = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    items = await service.list_items(db, source=source, limit=limit)
    out = []
    for it in items:
        runs = sorted(it.analysis_runs, key=lambda r: r.id, reverse=True)
        out.append(
            {
                "id": it.id,
                "source": it.source,
                "title": it.title,
                "address": it.address,
                "usage": it.usage,
                "case_no": it.case_no,
                "appraisal": triple_dict(it.appraisal_won),
                "min_bid": triple_dict(it.min_bid_won),
                "planned_price": triple_dict(it.planned_price_won),
                "digit_warnings": detect_digit_errors(
                    appraisal_won=it.appraisal_won,
                    min_bid_won=it.min_bid_won,
                    planned_price_won=it.planned_price_won,
                ),
                "verdict": runs[0].verdict if runs else "HOLD",
                "lat": it.lat,
                "lng": it.lng,
                "created_at": it.created_at,
            }
        )
    return out


@router.get("/items/{item_id}")
async def get_item(item_id: int, db: AsyncSession = Depends(get_db)):
    item = await service.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="not found")
    return service.serialize_detail(item)


@router.patch("/items/{item_id}/finance")
async def patch_finance(
    item_id: int,
    body: FinanceUpdate,
    db: AsyncSession = Depends(get_db),
):
    try:
        item = await service.update_finance(db, item_id, body)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return service.serialize_detail(item)


@router.post("/items/{item_id}/recompute")
async def recompute(item_id: int, db: AsyncSession = Depends(get_db)):
    try:
        item = await service.recompute(db, item_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return service.serialize_detail(item)


@router.get("/rules", response_model=list[RuleOut])
async def list_rules(db: AsyncSession = Depends(get_db)):
    await seed_rules(db)
    rows = (await db.execute(select(RuleConfig).order_by(RuleConfig.rule_key))).scalars().all()
    return [
        RuleOut(
            id=r.id,
            rule_key=r.rule_key,
            effective_from=r.effective_from.isoformat(),
            region_code=r.region_code,
            usage=r.usage,
            value_json=r.value_json,
            source_url=r.source_url,
            source_label=r.source_label,
            notes=r.notes,
        )
        for r in rows
    ]


@router.post("/items/{item_id}/documents")
async def upload_document(
    item_id: int,
    file: UploadFile = File(...),
    doc_type: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    data = await file.read()
    try:
        doc = await doc_service.upload_document(
            db,
            item_id,
            filename=file.filename or "upload.pdf",
            data=data,
            content_type=file.content_type or "application/pdf",
            doc_type_hint=doc_type,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return doc_service.serialize_document(doc)


@router.get("/documents/{doc_id}")
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await doc_service.get_document(db, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="not found")
    return doc_service.serialize_document(doc, include_pages=True)


@router.patch("/documents/{doc_id}")
async def correct_document(
    doc_id: int,
    body: DocumentCorrectIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        doc = await doc_service.correct_document(
            db,
            doc_id,
            doc_type=body.doc_type,
            extracted_text=body.extracted_text,
            confirm=body.confirm,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return doc_service.serialize_document(doc)


@router.post("/documents/{doc_id}/evidence")
async def document_evidence(
    doc_id: int,
    body: EvidenceIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await doc_service.page_evidence(
            db, doc_id, body.page, query=body.query
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/items/{item_id}/rights/from-evidence")
async def right_from_evidence(
    item_id: int,
    body: RightFromEvidenceIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await doc_service.attach_evidence_as_right(
            db,
            item_id,
            doc_id=body.doc_id,
            page=body.page,
            label=body.label,
            kind=body.kind,
            query=body.query,
            amount_won=body.amount_won,
            event_date=body.event_date,
            is_malso_baseline=body.is_malso_baseline,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return rights_service.serialize_right(entry)


@router.post("/items/{item_id}/rights")
async def create_right(
    item_id: int,
    body: RightCreateIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await rights_service.create_right(db, item_id, body.model_dump())
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return rights_service.serialize_right(entry)


@router.patch("/rights/{right_id}")
async def patch_right(
    right_id: int,
    body: RightPatchIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        entry = await rights_service.patch_right(
            db, right_id, body.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return rights_service.serialize_right(entry)


@router.delete("/rights/{right_id}")
async def delete_right(right_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await rights_service.delete_right(db, right_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"ok": True}


@router.post("/items/{item_id}/occupancies")
async def create_occupancy(
    item_id: int,
    body: OccupancyCreateIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        claim = await rights_service.create_occupancy(db, item_id, body.model_dump())
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return rights_service.serialize_occupancy(claim)


@router.patch("/occupancies/{occ_id}")
async def patch_occupancy(
    occ_id: int,
    body: OccupancyPatchIn,
    db: AsyncSession = Depends(get_db),
):
    try:
        claim = await rights_service.patch_occupancy(
            db, occ_id, body.model_dump(exclude_unset=True)
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return rights_service.serialize_occupancy(claim)


@router.delete("/occupancies/{occ_id}")
async def delete_occupancy(occ_id: int, db: AsyncSession = Depends(get_db)):
    try:
        await rights_service.delete_occupancy(db, occ_id)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"ok": True}


@router.post("/items/{item_id}/timeline/evaluate")
async def evaluate_timeline(
    item_id: int,
    body: TimelineEvaluateIn = TimelineEvaluateIn(),
    db: AsyncSession = Depends(get_db),
):
    try:
        return await rights_service.evaluate_item(
            db,
            item_id,
            apply_finance_suggest=body.apply_finance_suggest,
        )
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
