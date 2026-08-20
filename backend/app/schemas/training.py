from typing import Literal

from pydantic import BaseModel


class TrainRequest(BaseModel):
    scan_ids: list[str] | None = None  # None = use labels from all scans


class TrainJobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "completed", "failed"]
    detail: str | None = None
    metrics: dict | None = None
    model_version: str | None = None


class ActiveModelInfo(BaseModel):
    has_model: bool
    version: str | None = None
    metrics: dict | None = None
