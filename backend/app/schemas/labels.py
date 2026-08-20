from datetime import datetime, timezone

from pydantic import BaseModel, Field


class LabelIn(BaseModel):
    scan_id: str
    series: int
    i: int
    j: int
    contact_index: int


class LabelOut(LabelIn):
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
