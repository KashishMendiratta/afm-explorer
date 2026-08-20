from __future__ import annotations

import tempfile
from pathlib import Path

from afm_core.parsing import parse_afm_text
from afm_core.preprocessing import ScanCache, build_scan_cache

from app.core import storage
from app.core.config import Settings


def create_scan(settings: Settings, filename: str, content: bytes) -> tuple[str, ScanCache]:
    """Parse an uploaded AFM text export and persist it as a new scan."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=True) as tmp:
        tmp.write(content)
        tmp.flush()
        curves, meta = parse_afm_text(Path(tmp.name))
    meta.source_filename = filename  # restore the real filename (tempfile has a random one)

    cache = build_scan_cache(curves, meta)
    scan_id = storage.new_scan_id()
    storage.save_scan_cache(settings, scan_id, cache)
    return scan_id, cache


def get_scan_cache(settings: Settings, scan_id: str) -> ScanCache:
    return storage.load_scan_cache(settings, scan_id)


def list_scans(settings: Settings) -> list[dict]:
    return [storage.load_scan_summary(settings, sid) for sid in storage.list_scan_ids(settings)]
