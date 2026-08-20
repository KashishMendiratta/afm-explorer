"""Score a new curve with a trained contact-point model, returning a
FitResult with the same shape as afm_core.heuristics.sliding_window_fit —
so the backend and frontend can treat "heuristic" and "ml" estimates
interchangeably.
"""

from __future__ import annotations

import numpy as np
from afm_core.features import window_features
from afm_core.heuristics import all_windows
from afm_core.schemas import FitResult

from ml.train import TrainedContactModel


def estimate(d: np.ndarray, f: np.ndarray, model: TrainedContactModel) -> FitResult:
    n = len(d)
    windows = list(all_windows(n, model.window_size, model.step))
    if not windows:
        raise ValueError(f"curve has {n} points, shorter than window_size={model.window_size}")

    X = np.array(
        [window_features(d, f, start, end, n) for start, end in windows],
        dtype=np.float64,
    )
    # probability of the "is contact region" class
    proba = model.classifier.predict_proba(X)[:, 1]
    best_idx = int(np.argmax(proba))
    start, end = windows[best_idx]

    d_win, f_win = d[start:end], f[start:end]
    slope, intercept = np.polyfit(d_win, f_win, 1)
    f_pred = slope * d_win + intercept
    ss_res = float(np.sum((f_win - f_pred) ** 2))
    ss_tot = float(np.sum((f_win - np.mean(f_win)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return FitResult(
        slope=float(slope),
        intercept=float(intercept),
        start_index=start,
        end_index=end,
        r_squared=r_squared,
        method="ml",
    )


def qc_score(d: np.ndarray, f: np.ndarray, qc_model) -> float:
    """Higher = more anomalous. Wraps IsolationForest's score_samples so
    callers don't need to know the sign convention."""
    from afm_core.features import curve_features

    feats = np.array([curve_features(d, f)], dtype=np.float64)
    # score_samples: higher = more normal, so flip sign for "anomaly score"
    return float(-qc_model.score_samples(feats)[0])
