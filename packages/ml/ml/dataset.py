"""Build a windowed training set for the contact-point classifier from
hand-labeled curves.

Label efficiency trick: one human label (a single clicked contact index on
one curve) is expanded into every sliding window over that curve, each
becoming its own training row. A window is a positive example if the
labeled contact index falls inside it, negative otherwise. A curve with a
few hundred points and window_size=50/step=10 yields ~dozens of window rows
per label — so even 50-100 hand-labeled curves produce a few thousand
training examples, which is enough for a gradient-boosted tree model (see
train.py) without needing deep learning.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from afm_core.features import WINDOW_FEATURE_NAMES, window_features
from afm_core.heuristics import all_windows
from afm_core.preprocessing import ScanCache
from afm_core.schemas import Label


@dataclass
class WindowDataset:
    X: np.ndarray  # (n_samples, n_features)
    y: np.ndarray  # (n_samples,) 0/1
    groups: np.ndarray  # (n_samples,) curve id string, for group-aware splits
    feature_names: list[str]


def build_window_dataset(
    scan_caches: dict[str, ScanCache],
    labels: list[Label],
    window_size: int = 50,
    step: int = 10,
) -> WindowDataset:
    rows: list[list[float]] = []
    y: list[int] = []
    groups: list[str] = []

    skipped = 0
    for label in labels:
        cache = scan_caches.get(label.scan_id)
        if cache is None:
            skipped += 1
            continue
        key = label.key.as_tuple()
        curve = cache.curves.get(key)
        if curve is None:
            skipped += 1
            continue

        d, f = curve.distance, curve.force
        n = len(d)
        curve_id = f"{label.scan_id}:{label.key}"

        for start, end in all_windows(n, window_size, step):
            feats = window_features(d, f, start, end, n)
            is_positive = start <= label.contact_index < end
            rows.append(feats)
            y.append(1 if is_positive else 0)
            groups.append(curve_id)

    if not rows:
        raise ValueError(
            f"no usable labels to build a dataset from ({skipped} labels skipped "
            "because their scan/curve was not found)"
        )

    return WindowDataset(
        X=np.array(rows, dtype=np.float64),
        y=np.array(y, dtype=np.int64),
        groups=np.array(groups),
        feature_names=list(WINDOW_FEATURE_NAMES),
    )
