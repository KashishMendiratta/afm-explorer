"""Orchestrates a training run: gather labels -> build dataset -> train
contact-point classifier + QC model -> evaluate against the classical
heuristic -> persist as a new model version -> promote to active.

Runs via FastAPI BackgroundTasks with an in-memory job-status dict. This is
intentionally lightweight (no Celery/Redis) because training a
HistGradientBoostingClassifier on a few thousand window rows takes seconds,
not minutes — see the plan doc / README for why a heavier task queue isn't
warranted at this project's scale.
"""

from __future__ import annotations

import threading
import time
import uuid

from afm_core.schemas import Label

from app.core.config import Settings
from app.services import label_service, model_registry, scan_service

_jobs_lock = threading.Lock()
_jobs: dict[str, dict] = {}


def _set_job(job_id: str, **fields) -> None:
    with _jobs_lock:
        _jobs[job_id] = {**_jobs.get(job_id, {}), "job_id": job_id, **fields}


def get_job(job_id: str) -> dict | None:
    with _jobs_lock:
        return dict(_jobs[job_id]) if job_id in _jobs else None


def start_training(settings: Settings, scan_ids: list[str] | None) -> str:
    job_id = uuid.uuid4().hex[:10]
    _set_job(job_id, status="pending", detail=None, metrics=None, model_version=None)
    return job_id


def run_training_job(job_id: str, settings: Settings, scan_ids: list[str] | None) -> None:
    # imports deferred so `ml` (scikit-learn etc.) is only required at
    # train time, not at basic API-server import time
    from ml.dataset import build_window_dataset
    from ml.evaluate import evaluate_baseline_vs_ml, split_labels_by_curve
    from ml.persistence import save_bundle
    from ml.train import train_contact_point_model, train_qc_model

    _set_job(job_id, status="running")
    try:
        labels: list[Label] = label_service.list_labels(settings)
        if scan_ids:
            labels = [lbl for lbl in labels if lbl.scan_id in scan_ids]
        if not labels:
            raise ValueError("no labels found — label some curves via POST /api/labels first")

        relevant_scan_ids = sorted({lbl.scan_id for lbl in labels})
        scan_caches = {sid: scan_service.get_scan_cache(settings, sid) for sid in relevant_scan_ids}

        train_labels, eval_labels = split_labels_by_curve(labels, test_frac=0.3)
        if not train_labels:
            train_labels, eval_labels = labels, []

        dataset = build_window_dataset(scan_caches, train_labels, settings.window_size, settings.window_step)
        contact_model = train_contact_point_model(
            dataset, window_size=settings.window_size, step=settings.window_step
        )

        qc_model = None
        try:
            qc_model = train_qc_model(scan_caches)
        except ValueError:
            pass  # not enough curves for QC yet; contact-point model still ships

        eval_summary = {}
        if eval_labels:
            report = evaluate_baseline_vs_ml(scan_caches, eval_labels, contact_model)
            eval_summary = {
                "n_eval_curves": report.n_curves,
                "heuristic_mean_abs_error": report.heuristic_mean_abs_error,
                "ml_mean_abs_error": report.ml_mean_abs_error,
                "heuristic_median_abs_error": report.heuristic_median_abs_error,
                "ml_median_abs_error": report.ml_median_abs_error,
            }

        metrics = {**contact_model.metrics, "evaluation": eval_summary, "has_qc_model": qc_model is not None}

        version = time.strftime("%Y%m%dT%H%M%S") + f"-{job_id}"
        save_bundle(model_registry.bundle_path(settings, version), contact_model, qc_model, metrics)
        model_registry.set_active_version(settings, version, metrics)

        _set_job(job_id, status="completed", metrics=metrics, model_version=version, detail=None)
    except Exception as exc:  # noqa: BLE001 - report any failure back via job status
        _set_job(job_id, status="failed", detail=str(exc))
