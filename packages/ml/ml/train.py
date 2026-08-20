"""Train the two AI models:

1. contact-point classifier (supervised): HistGradientBoostingClassifier
   over window-level features (see dataset.py). Chosen over a neural net
   because the realistic label budget for this project (tens to a couple
   hundred hand-labeled curves) is far too small to train a deep model
   without overfitting; gradient boosting on engineered features is the
   standard, defensible choice at this data scale.

2. curve quality-control model (unsupervised): IsolationForest over
   whole-curve features (see afm_core.features.curve_features). Requires no
   labels at all, so it can run on every curve in a scan, not just labeled
   ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from afm_core.features import curve_features
from afm_core.preprocessing import ScanCache
from sklearn.ensemble import HistGradientBoostingClassifier, IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit

from ml.dataset import WindowDataset


@dataclass
class TrainedContactModel:
    classifier: HistGradientBoostingClassifier
    window_size: int
    step: int
    feature_names: list[str]
    metrics: dict = field(default_factory=dict)


def train_contact_point_model(
    dataset: WindowDataset,
    window_size: int = 50,
    step: int = 10,
    test_size: float = 0.25,
    random_state: int = 0,
) -> TrainedContactModel:
    n_positive_groups = len(set(dataset.groups[dataset.y == 1]))
    if n_positive_groups < 2:
        raise ValueError(
            "need labels on at least 2 distinct curves to train/evaluate a split; "
            f"got positives on {n_positive_groups}"
        )

    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(splitter.split(dataset.X, dataset.y, groups=dataset.groups))

    clf = HistGradientBoostingClassifier(
        max_iter=200,
        class_weight="balanced",
        random_state=random_state,
    )
    clf.fit(dataset.X[train_idx], dataset.y[train_idx])

    y_pred = clf.predict(dataset.X[test_idx])
    y_true = dataset.y[test_idx]
    metrics = {
        "n_train_rows": int(len(train_idx)),
        "n_test_rows": int(len(test_idx)),
        "n_labeled_curves": int(len(set(dataset.groups))),
        "window_f1": float(f1_score(y_true, y_pred, zero_division=0)),
        "window_precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "window_recall": float(recall_score(y_true, y_pred, zero_division=0)),
    }

    return TrainedContactModel(
        classifier=clf,
        window_size=window_size,
        step=step,
        feature_names=dataset.feature_names,
        metrics=metrics,
    )


def train_qc_model(scan_caches: dict[str, ScanCache], contamination: float = 0.1) -> IsolationForest:
    rows = []
    for cache in scan_caches.values():
        for curve in cache.curves.values():
            rows.append(curve_features(curve.distance, curve.force))

    if len(rows) < 10:
        raise ValueError(f"need at least 10 curves to fit a QC model, got {len(rows)}")

    X = np.array(rows, dtype=np.float64)
    model = IsolationForest(contamination=contamination, random_state=0)
    model.fit(X)
    return model
