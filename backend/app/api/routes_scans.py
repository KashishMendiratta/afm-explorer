from __future__ import annotations

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile

from app.api.deps import Settings, get_settings
from app.core import storage
from app.schemas.scans import HeatmapResponse, ScanMetaOut, ScanSummary, ScanUploadResponse
from app.services import estimate_service, scan_service

router = APIRouter(prefix="/api/scans", tags=["scans"])


def _nan_to_none(matrix: np.ndarray) -> list[list[float | None]]:
    return [[None if np.isnan(v) else float(v) for v in row] for row in matrix]


@router.post("", response_model=ScanUploadResponse)
async def upload_scan(file: UploadFile, settings: Settings = Depends(get_settings)):
    content = await file.read()
    try:
        scan_id, cache = scan_service.create_scan(settings, file.filename or "upload.txt", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScanUploadResponse(
        scan_id=scan_id, m=cache.m, n=cache.n, n_series=cache.n_series, n_curves=len(cache.curves)
    )


@router.get("", response_model=list[ScanSummary])
def list_scans(settings: Settings = Depends(get_settings)):
    summaries = scan_service.list_scans(settings)
    return [
        ScanSummary(
            scan_id=s["scan_id"],
            m=s["m"],
            n=s["n"],
            n_series=s["n_series"],
            source_filename=s["meta"]["source_filename"],
            meta=ScanMetaOut(**{k: s["meta"][k] for k in ScanMetaOut.model_fields}),
        )
        for s in summaries
    ]


@router.get("/{scan_id}", response_model=ScanSummary)
def get_scan(scan_id: str, settings: Settings = Depends(get_settings)):
    try:
        s = storage.load_scan_summary(settings, scan_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ScanSummary(
        scan_id=s["scan_id"],
        m=s["m"],
        n=s["n"],
        n_series=s["n_series"],
        source_filename=s["meta"]["source_filename"],
        meta=ScanMetaOut(**{k: s["meta"][k] for k in ScanMetaOut.model_fields}),
    )


@router.get("/{scan_id}/heightmap", response_model=HeatmapResponse)
def get_heightmap(scan_id: str, series: int = 0, settings: Settings = Depends(get_settings)):
    cache = _load_cache_or_404(settings, scan_id)
    H = cache.height_map(series=series)
    return HeatmapResponse(scan_id=scan_id, series=series, kind="height", m=cache.m, n=cache.n, values=_nan_to_none(H))


@router.get("/{scan_id}/stiffnessmap", response_model=HeatmapResponse)
def get_stiffnessmap(
    scan_id: str,
    series: int = 0,
    method: str = Query("heuristic", pattern="^(heuristic|ml)$"),
    settings: Settings = Depends(get_settings),
):
    cache = _load_cache_or_404(settings, scan_id)
    try:
        M = estimate_service.stiffness_map(settings, cache, series, method)
    except LookupError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return HeatmapResponse(
        scan_id=scan_id, series=series, kind="stiffness", method=method, m=cache.m, n=cache.n, values=_nan_to_none(M)
    )


def _load_cache_or_404(settings: Settings, scan_id: str):
    try:
        return scan_service.get_scan_cache(settings, scan_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
