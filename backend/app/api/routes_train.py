from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.api.deps import Settings, get_settings
from app.core.security import require_api_key
from app.schemas.training import ActiveModelInfo, TrainJobStatus, TrainRequest
from app.services import model_registry, train_service

router = APIRouter(prefix="/api", tags=["training"])


@router.post("/train", response_model=TrainJobStatus, dependencies=[Depends(require_api_key)])
def trigger_training(
    req: TrainRequest, background_tasks: BackgroundTasks, settings: Settings = Depends(get_settings)
):
    job_id = train_service.start_training(settings, req.scan_ids)
    background_tasks.add_task(train_service.run_training_job, job_id, settings, req.scan_ids)
    return TrainJobStatus(job_id=job_id, status="pending")


@router.get("/train/{job_id}", response_model=TrainJobStatus)
def get_training_status(job_id: str):
    job = train_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job_id")
    return TrainJobStatus(**job)


@router.get("/models/active", response_model=ActiveModelInfo)
def get_active_model(settings: Settings = Depends(get_settings)):
    info = model_registry.get_active_version_info(settings)
    if info is None:
        return ActiveModelInfo(has_model=False)
    return ActiveModelInfo(has_model=True, version=info["active"], metrics=info.get("metrics"))
