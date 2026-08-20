"""Benchmark the trained ML contact-point model against the classical
afm_core.heuristics baseline on held-out labeled curves.

This is the concrete artifact that answers "does the AI feature actually
help?" — a per-curve table plus summary statistics, not just window-level
F1. Both estimators are scored against the same human-provided ground
truth, on curves neither the classifier nor the heuristic's own
"best window" selection has seen as a label during training.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
from afm_core.heuristics import sliding_window_fit
from afm_core.preprocessing import ScanCache
from afm_core.schemas import Label

from ml.infer import estimate
from ml.train import TrainedContactModel


@dataclass
class CurveComparison:
    scan_id: str
    curve: str
    true_index: int
    heuristic_index: int | None
    ml_index: int | None
    heuristic_abs_error: float | None
    ml_abs_error: float | None


@dataclass
class EvaluationReport:
    n_curves: int
    heuristic_mean_abs_error: float | None
    ml_mean_abs_error: float | None
    heuristic_median_abs_error: float | None
    ml_median_abs_error: float | None
    per_curve: list[CurveComparison]


def split_labels_by_curve(
    labels: list[Label], test_frac: float = 0.3, seed: int = 0
) -> tuple[list[Label], list[Label]]:
    """Curve-level (not window-level) train/test split so no window from an
    evaluation curve leaks into training."""
    rng = random.Random(seed)
    shuffled = labels[:]
    rng.shuffle(shuffled)
    n_test = max(1, int(len(shuffled) * test_frac)) if len(shuffled) > 1 else 0
    return shuffled[n_test:], shuffled[:n_test]


def evaluate_baseline_vs_ml(
    scan_caches: dict[str, ScanCache],
    eval_labels: list[Label],
    model: TrainedContactModel,
) -> EvaluationReport:
    comparisons: list[CurveComparison] = []

    for label in eval_labels:
        cache = scan_caches.get(label.scan_id)
        if cache is None:
            continue
        curve = cache.curves.get(label.key.as_tuple())
        if curve is None:
            continue

        d, f = curve.distance, curve.force

        heuristic_index = None
        heuristic_err = None
        try:
            h_fit = sliding_window_fit(d, f, window_size=model.window_size, step=model.step)
            heuristic_index = h_fit.contact_index
            heuristic_err = abs(heuristic_index - label.contact_index)
        except ValueError:
            pass

        ml_index = None
        ml_err = None
        try:
            m_fit = estimate(d, f, model)
            ml_index = m_fit.contact_index
            ml_err = abs(ml_index - label.contact_index)
        except ValueError:
            pass

        comparisons.append(
            CurveComparison(
                scan_id=label.scan_id,
                curve=str(label.key),
                true_index=label.contact_index,
                heuristic_index=heuristic_index,
                ml_index=ml_index,
                heuristic_abs_error=heuristic_err,
                ml_abs_error=ml_err,
            )
        )

    h_errors = [c.heuristic_abs_error for c in comparisons if c.heuristic_abs_error is not None]
    m_errors = [c.ml_abs_error for c in comparisons if c.ml_abs_error is not None]

    return EvaluationReport(
        n_curves=len(comparisons),
        heuristic_mean_abs_error=float(np.mean(h_errors)) if h_errors else None,
        ml_mean_abs_error=float(np.mean(m_errors)) if m_errors else None,
        heuristic_median_abs_error=float(np.median(h_errors)) if h_errors else None,
        ml_median_abs_error=float(np.median(m_errors)) if m_errors else None,
        per_curve=comparisons,
    )
