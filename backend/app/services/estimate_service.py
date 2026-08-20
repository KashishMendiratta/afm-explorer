from __future__ import annotations

from afm_core.heuristics import sliding_window_fit
from afm_core.preprocessing import ScanCache
from afm_core.schemas import FitResult

from app.core.config import Settings
from app.services import model_registry


def estimate(settings: Settings, cache: ScanCache, series: int, i: int, j: int, method: str) -> FitResult:
    curve = cache.curve(series, i, j)

    if method == "heuristic":
        return sliding_window_fit(curve.distance, curve.force, settings.window_size, settings.window_step)

    if method == "ml":
        bundle = model_registry.get_active_bundle(settings)
        if bundle is None:
            raise LookupError("no trained ML model is available yet — POST /api/train first")
        contact_model, _qc_model, _metrics = bundle
        from ml.infer import estimate as ml_estimate

        return ml_estimate(curve.distance, curve.force, contact_model)

    raise ValueError(f"unknown method: {method!r} (expected 'heuristic' or 'ml')")


def stiffness_map(settings: Settings, cache: ScanCache, series: int, method: str):
    if method == "heuristic":
        return cache.stiffness_map(series=series)

    if method == "ml":
        bundle = model_registry.get_active_bundle(settings)
        if bundle is None:
            raise LookupError("no trained ML model is available yet — POST /api/train first")
        contact_model, _qc_model, _metrics = bundle
        from ml.infer import estimate as ml_estimate

        return cache.stiffness_map(series=series, estimator=lambda d, f: ml_estimate(d, f, contact_model))

    raise ValueError(f"unknown method: {method!r} (expected 'heuristic' or 'ml')")
