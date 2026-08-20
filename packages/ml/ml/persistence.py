"""joblib-based persistence for a trained model bundle (contact-point
classifier + optional QC model + metadata). Kept deliberately simple
(single file per version) — see backend/app/core/config.py for where
bundles are stored and backend/app/services/train_service.py for the
save/load + "active version" registry logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import joblib

from ml.train import TrainedContactModel


def save_bundle(path: Path, contact_model: TrainedContactModel, qc_model: Any | None, metrics: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "classifier": contact_model.classifier,
            "window_size": contact_model.window_size,
            "step": contact_model.step,
            "feature_names": contact_model.feature_names,
            "contact_metrics": contact_model.metrics,
            "qc_model": qc_model,
            "metrics": metrics,
        },
        path,
    )


def load_bundle(path: Path) -> tuple[TrainedContactModel, Any | None, dict]:
    bundle = joblib.load(path)
    contact_model = TrainedContactModel(
        classifier=bundle["classifier"],
        window_size=bundle["window_size"],
        step=bundle["step"],
        feature_names=bundle["feature_names"],
        metrics=bundle.get("contact_metrics", {}),
    )
    return contact_model, bundle.get("qc_model"), bundle.get("metrics", {})
