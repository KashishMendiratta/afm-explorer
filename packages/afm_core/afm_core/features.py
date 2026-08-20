"""Feature engineering shared by the classical heuristic's evaluation and
the ML contact-point classifier (packages/ml).

Two feature sets:
  - window_features: per-window features (used to train/score the
    contact-point classifier — one row per sliding-window candidate).
  - curve_features: per-curve features (used by the unsupervised
    IsolationForest quality-control model — one row per whole curve).
"""

from __future__ import annotations

import numpy as np

WINDOW_FEATURE_NAMES = [
    "slope",
    "r_squared",
    "curvature",
    "local_std",
    "position_frac",
    "f_mean",
    "f_range",
]

CURVE_FEATURE_NAMES = [
    "n_points",
    "d_range",
    "f_range",
    "f_std",
    "diff_std",
    "monotonic_violation_frac",
    "max_abs_second_diff",
]


def window_features(d: np.ndarray, f: np.ndarray, start: int, end: int, n_total: int) -> list[float]:
    """Compute a fixed-length feature vector for one candidate window.

    Order matches WINDOW_FEATURE_NAMES.
    """
    d_win, f_win = d[start:end], f[start:end]
    if len(d_win) < 2:
        return [0.0] * len(WINDOW_FEATURE_NAMES)

    slope, intercept = np.polyfit(d_win, f_win, 1)
    f_pred = slope * d_win + intercept
    ss_res = float(np.sum((f_win - f_pred) ** 2))
    ss_tot = float(np.sum((f_win - np.mean(f_win)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # curvature: mean absolute second difference of the (smoothed) force
    # trace inside the window — high for the noisy pre-contact region, low
    # for the genuinely linear contact region.
    if len(f_win) >= 3:
        second_diff = np.diff(f_win, n=2)
        curvature = float(np.mean(np.abs(second_diff)))
    else:
        curvature = 0.0

    local_std = float(np.std(f_win - f_pred))
    position_frac = start / max(n_total - 1, 1)
    f_mean = float(np.mean(f_win))
    f_range = float(np.max(f_win) - np.min(f_win))

    return [slope, r_squared, curvature, local_std, position_frac, f_mean, f_range]


def curve_features(d: np.ndarray, f: np.ndarray) -> list[float]:
    """Compute a fixed-length, whole-curve feature vector for QC / anomaly
    detection. Order matches CURVE_FEATURE_NAMES.
    """
    n_points = len(d)
    if n_points < 3:
        return [float(n_points), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

    d_range = float(np.max(d) - np.min(d))
    f_range = float(np.max(f) - np.min(f))
    f_std = float(np.std(f))
    diffs = np.diff(f)
    diff_std = float(np.std(diffs))

    # In a well-behaved push curve, distance should move roughly
    # monotonically; a high violation fraction suggests a noisy/bad curve.
    d_diffs = np.diff(d)
    if len(d_diffs) > 0:
        sign = np.sign(np.median(d_diffs)) or 1.0
        monotonic_violation_frac = float(np.mean(np.sign(d_diffs) != sign))
    else:
        monotonic_violation_frac = 0.0

    second_diff = np.diff(f, n=2) if n_points >= 3 else np.array([0.0])
    max_abs_second_diff = float(np.max(np.abs(second_diff))) if len(second_diff) else 0.0

    return [
        float(n_points),
        d_range,
        f_range,
        f_std,
        diff_std,
        monotonic_violation_frac,
        max_abs_second_diff,
    ]
