"""Classical sliding-window linear-fit heuristic for locating the contact
region of an AFM force-distance curve.

This consolidates estimate_afm.py's approach (chosen as the one classical
baseline, see repo README for why the other two heuristics from afm.py and
app2.py were retired rather than kept as parallel implementations): slide a
fixed-size window across the curve, fit a line in each window, and pick the
window with the lowest residual sum of squares as the contact region.
"""

from __future__ import annotations

import numpy as np

from afm_core.schemas import FitResult

DEFAULT_WINDOW_SIZE = 50
DEFAULT_STEP = 10


def _linear_fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    """Least-squares line fit; returns (slope, intercept, r_squared).

    Uses numpy.polyfit instead of scipy.optimize.curve_fit (as the original
    script did) — algebraically identical result for a linear model, no
    iterative optimizer needed, and one fewer runtime dependency.
    """
    if len(x) < 2:
        return 0.0, float(y[0]) if len(y) else 0.0, 0.0
    slope, intercept = np.polyfit(x, y, 1)
    y_pred = slope * x + intercept
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return float(slope), float(intercept), r_squared


def sliding_window_fit(
    d: np.ndarray,
    f: np.ndarray,
    window_size: int = DEFAULT_WINDOW_SIZE,
    step: int = DEFAULT_STEP,
) -> FitResult:
    """Find the window with the lowest fit residual and report its slope.

    Raises ValueError if the curve is shorter than one window.
    """
    n = len(d)
    if n < window_size:
        raise ValueError(f"curve has {n} points, shorter than window_size={window_size}")

    best_start = 0
    best_end = window_size
    best_slope = 0.0
    best_intercept = 0.0
    best_r_squared = 0.0
    min_residual = float("inf")

    for start in range(0, n - window_size + 1, step):
        end = start + window_size
        d_win, f_win = d[start:end], f[start:end]
        slope, intercept, r_squared = _linear_fit(d_win, f_win)
        residual = float(np.sum((f_win - (slope * d_win + intercept)) ** 2))
        if residual < min_residual:
            min_residual = residual
            best_start, best_end = start, end
            best_slope, best_intercept, best_r_squared = slope, intercept, r_squared

    return FitResult(
        slope=best_slope,
        intercept=best_intercept,
        start_index=best_start,
        end_index=best_end,
        r_squared=best_r_squared,
        method="heuristic",
    )


def all_windows(n_points: int, window_size: int = DEFAULT_WINDOW_SIZE, step: int = DEFAULT_STEP):
    """Yield (start, end) pairs for every window over a curve of n_points.

    Shared by the heuristic search above and by ml.dataset, which turns each
    window into one training example for the contact-point classifier.
    """
    for start in range(0, max(n_points - window_size + 1, 0), step):
        yield start, start + window_size
