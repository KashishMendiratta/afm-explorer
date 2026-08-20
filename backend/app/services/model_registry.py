"""In-process cache + on-disk registry for the active trained ML model
bundle. A real production deployment would use a model registry service
(e.g. MLflow) or at least a database row instead of a JSON pointer file —
noted in the README as a scaling consideration deliberately out of scope
for this project's size.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

from app.core.config import Settings

_lock = threading.Lock()
_cache: dict[str, Any] = {}  # {"version": str, "bundle": (contact_model, qc_model, metrics)}


def registry_path(settings: Settings) -> Path:
    return settings.models_dir / "registry.json"


def set_active_version(settings: Settings, version: str, metrics: dict) -> None:
    registry_path(settings).write_text(json.dumps({"active": version, "metrics": metrics}, indent=2))
    with _lock:
        _cache.pop("version", None)  # force reload on next access


def get_active_version_info(settings: Settings) -> dict | None:
    path = registry_path(settings)
    if not path.exists():
        return None
    return json.loads(path.read_text())


def bundle_path(settings: Settings, version: str) -> Path:
    return settings.models_dir / version / "bundle.joblib"


def get_active_bundle(settings: Settings):
    """Returns (contact_model, qc_model, metrics) for the active model
    version, or None if no model has been trained yet. Cached in-process."""
    info = get_active_version_info(settings)
    if info is None:
        return None

    version = info["active"]
    with _lock:
        if _cache.get("version") == version and "bundle" in _cache:
            return _cache["bundle"]

    from ml.persistence import load_bundle  # local import: keep ml optional at import time

    bundle = load_bundle(bundle_path(settings, version))
    with _lock:
        _cache["version"] = version
        _cache["bundle"] = bundle
    return bundle
