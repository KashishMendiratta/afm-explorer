from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import Settings, get_settings
from app.schemas.curves import CurveOut, FitResultOut
from app.services import estimate_service, scan_service

router = APIRouter(prefix="/api/scans/{scan_id}/curves", tags=["curves"])


def _cache_or_404(settings: Settings, scan_id: str):
    try:
        return scan_service.get_scan_cache(settings, scan_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _curve_or_404(cache, series: int, i: int, j: int):
    try:
        return cache.curve(series, i, j)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"no curve at series={series}, i={i}, j={j}") from exc


@router.get("/{series}/{i}/{j}", response_model=CurveOut)
def get_curve(scan_id: str, series: int, i: int, j: int, settings: Settings = Depends(get_settings)):
    cache = _cache_or_404(settings, scan_id)
    curve = _curve_or_404(cache, series, i, j)
    return CurveOut(
        scan_id=scan_id,
        series=series,
        i=i,
        j=j,
        distance=curve.distance.tolist(),
        force=curve.force.tolist(),
    )


@router.get("/{series}/{i}/{j}/estimate", response_model=FitResultOut)
def get_estimate(
    scan_id: str,
    series: int,
    i: int,
    j: int,
    method: str = Query("heuristic", pattern="^(heuristic|ml)$"),
    settings: Settings = Depends(get_settings),
):
    cache = _cache_or_404(settings, scan_id)
    _curve_or_404(cache, series, i, j)  # 404 before 409/400
    try:
        fit = estimate_service.estimate(settings, cache, series, i, j, method)
    except LookupError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return FitResultOut(
        scan_id=scan_id,
        series=series,
        i=i,
        j=j,
        method=fit.method,
        slope=fit.slope,
        intercept=fit.intercept,
        start_index=fit.start_index,
        end_index=fit.end_index,
        contact_index=fit.contact_index,
        r_squared=fit.r_squared,
    )
