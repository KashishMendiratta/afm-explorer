from __future__ import annotations

from datetime import datetime, timezone

from afm_core.schemas import CurveKey, Label

from app.core import storage
from app.core.config import Settings


def add_label(settings: Settings, scan_id: str, series: int, i: int, j: int, contact_index: int) -> Label:
    label = Label(
        scan_id=scan_id,
        key=CurveKey(series, i, j),
        contact_index=contact_index,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    storage.append_label(settings, label)
    return label


def list_labels(settings: Settings, scan_id: str | None = None) -> list[Label]:
    return storage.load_labels(settings, scan_id)
