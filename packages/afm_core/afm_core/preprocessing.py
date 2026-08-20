"""Scan-level preprocessing: turns a parsed set of curves into the cached,
backend-owned artifacts the API and frontend actually consume.

This replaces a step that existed only implicitly in the original project:
afm.py / app2.py expected a pre-built '{prefix}.data.pickled' +
'{prefix}.heights.npy' pair, but no script producing them was included.
Two deliberate design changes from that original approach:

1. No pickle. The backend accepts a raw '.txt' upload and parses it itself
   (via afm_core.parsing); it never unpickles a file from a client, which
   would be an arbitrary-code-execution risk for a networked service.
2. No separate proprietary topography file. The original height map came
   from an instrument-specific file format that isn't part of this project.
   Instead, ScanCache derives an approximate height map from the force
   curves themselves: for each (i, j) pixel, the surface height is taken as
   the distance (d) coordinate at the estimated contact point of the
   extend/push (series 0) curve. This is a documented approximation, not a
   faithful re-derivation of the original instrument's topography channel.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from afm_core.heuristics import sliding_window_fit
from afm_core.schemas import Curve, ScanMeta


@dataclass
class ScanCache:
    meta: ScanMeta
    curves: dict[tuple[int, int, int], Curve]
    m: int  # grid rows (max i + 1)
    n: int  # grid cols (max j + 1)
    n_series: int

    def curve(self, s: int, i: int, j: int) -> Curve:
        return self.curves[(s, i, j)]

    def height_map(self, series: int = 0) -> np.ndarray:
        """Approximate topography: per-pixel distance at the heuristic
        contact point of the given series (default: push/extend curves).
        NaN where a curve is missing or the heuristic fit fails.
        """
        H = np.full((self.m, self.n), np.nan, dtype=np.float64)
        for (s, i, j), curve in self.curves.items():
            if s != series:
                continue
            try:
                fit = sliding_window_fit(curve.distance, curve.force)
                H[i, j] = curve.distance[fit.contact_index]
            except ValueError:
                continue
        return H

    def stiffness_map(self, series: int = 0, estimator=None) -> np.ndarray:
        """Per-pixel stiffness (slope) map. `estimator` is a callable
        (d, f) -> FitResult; defaults to the classical sliding-window
        heuristic. Pass ml.infer.estimate for the trained-model version.
        """
        if estimator is None:
            estimator = sliding_window_fit
        M = np.full((self.m, self.n), np.nan, dtype=np.float64)
        for (s, i, j), curve in self.curves.items():
            if s != series:
                continue
            try:
                fit = estimator(curve.distance, curve.force)
                M[i, j] = fit.slope
            except ValueError:
                continue
        return M


def build_scan_cache(curves: dict[tuple[int, int, int], Curve], meta: ScanMeta) -> ScanCache:
    if not curves:
        raise ValueError("no curves parsed from source file")
    max_i = max(k[1] for k in curves)
    max_j = max(k[2] for k in curves)
    n_series = 1 + max(k[0] for k in curves)
    m = meta.i_length if meta.i_length is not None else max_i + 1
    n = meta.j_length if meta.j_length is not None else max_j + 1
    return ScanCache(meta=meta, curves=curves, m=m, n=n, n_series=n_series)
