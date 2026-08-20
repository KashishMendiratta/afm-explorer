from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.deps import Settings, get_settings
from app.schemas.labels import LabelIn, LabelOut
from app.services import label_service

router = APIRouter(prefix="/api/labels", tags=["labels"])


@router.post("", response_model=LabelOut)
def create_label(label: LabelIn, settings: Settings = Depends(get_settings)):
    saved = label_service.add_label(
        settings, label.scan_id, label.series, label.i, label.j, label.contact_index
    )
    return LabelOut(
        scan_id=saved.scan_id,
        series=saved.key.series,
        i=saved.key.i,
        j=saved.key.j,
        contact_index=saved.contact_index,
        created_at=saved.created_at,
    )


@router.get("", response_model=list[LabelOut])
def get_labels(scan_id: str | None = Query(None), settings: Settings = Depends(get_settings)):
    labels = label_service.list_labels(settings, scan_id)
    return [
        LabelOut(
            scan_id=lbl.scan_id,
            series=lbl.key.series,
            i=lbl.key.i,
            j=lbl.key.j,
            contact_index=lbl.contact_index,
            created_at=lbl.created_at or "",
        )
        for lbl in labels
    ]
