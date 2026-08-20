"""Backend-owned persistence for parsed scans, labels, and trained models.

Deliberately simple (filesystem + npz/json/jsonl) rather than a database —
appropriate for a single-instance demo deployment. Swapping this module for
a real database/object-store backed implementation is called out in the
README as a natural next step for a production version.
"""

from __future__ import annotations

import json
import uuid

import numpy as np
from afm_core.preprocessing import ScanCache, build_scan_cache
from afm_core.schemas import Curve, CurveKey, Label, ScanMeta

from app.core.config import Settings


def new_scan_id() -> str:
    return uuid.uuid4().hex[:12]


def save_scan_cache(settings: Settings, scan_id: str, cache: ScanCache) -> None:
    scan_dir = settings.scans_dir / scan_id
    scan_dir.mkdir(parents=True, exist_ok=True)

    arrays: dict[str, np.ndarray] = {}
    for (s, i, j), curve in cache.curves.items():
        arrays[f"{s}_{i}_{j}_d"] = curve.distance
        arrays[f"{s}_{i}_{j}_f"] = curve.force
    np.savez_compressed(scan_dir / "curves.npz", **arrays)

    meta_out = {
        "scan_id": scan_id,
        "m": cache.m,
        "n": cache.n,
        "n_series": cache.n_series,
        "meta": cache.meta.__dict__,
    }
    (scan_dir / "meta.json").write_text(json.dumps(meta_out, indent=2))


def load_scan_cache(settings: Settings, scan_id: str) -> ScanCache:
    scan_dir = settings.scans_dir / scan_id
    if not scan_dir.exists():
        raise FileNotFoundError(f"unknown scan_id: {scan_id}")

    meta_out = json.loads((scan_dir / "meta.json").read_text())
    meta = ScanMeta(**meta_out["meta"])

    npz = np.load(scan_dir / "curves.npz")
    curves: dict[tuple[int, int, int], Curve] = {}
    seen: set[tuple[int, int, int]] = set()
    for key_name in npz.files:
        s, i, j, kind = key_name.split("_")
        s, i, j = int(s), int(i), int(j)
        if (s, i, j) in seen:
            continue
        seen.add((s, i, j))
        curves[(s, i, j)] = Curve(
            key=CurveKey(s, i, j),
            distance=npz[f"{s}_{i}_{j}_d"],
            force=npz[f"{s}_{i}_{j}_f"],
        )

    return build_scan_cache(curves, meta)


def list_scan_ids(settings: Settings) -> list[str]:
    if not settings.scans_dir.exists():
        return []
    return sorted(p.name for p in settings.scans_dir.iterdir() if p.is_dir())


def load_scan_summary(settings: Settings, scan_id: str) -> dict:
    scan_dir = settings.scans_dir / scan_id
    meta_out = json.loads((scan_dir / "meta.json").read_text())
    return meta_out


# --- labels ---------------------------------------------------------------


def append_label(settings: Settings, label: Label) -> None:
    record = {
        "scan_id": label.scan_id,
        "series": label.key.series,
        "i": label.key.i,
        "j": label.key.j,
        "contact_index": label.contact_index,
        "created_at": label.created_at,
    }
    with open(settings.labels_path, "a") as f:
        f.write(json.dumps(record) + "\n")


def load_labels(settings: Settings, scan_id: str | None = None) -> list[Label]:
    """Loads labels, keeping only the most recent one per (scan_id, curve)
    — the label file is append-only, so re-labeling a curve just adds a
    newer record rather than overwriting, and we resolve that here rather
    than on write to keep append_label a simple, crash-safe operation."""
    path = settings.labels_path
    if not path.exists():
        return []
    latest: dict[tuple, Label] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if scan_id is not None and rec["scan_id"] != scan_id:
            continue
        dedup_key = (rec["scan_id"], rec["series"], rec["i"], rec["j"])
        latest[dedup_key] = Label(
            scan_id=rec["scan_id"],
            key=CurveKey(rec["series"], rec["i"], rec["j"]),
            contact_index=rec["contact_index"],
            created_at=rec.get("created_at"),
        )
    return list(latest.values())
