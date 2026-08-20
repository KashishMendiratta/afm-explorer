"""afm_core: shared parsing, heuristic fitting, and feature-extraction library.

Consolidates logic that previously existed as three separate, drifting
copies across estimate_afm.py, plotafm.py, afm.py, and app2.py (see
/legacy_scripts in the repo root for the originals, kept for reference).
"""

from afm_core import features
from afm_core.heuristics import sliding_window_fit
from afm_core.parsing import parse_afm_text
from afm_core.schemas import Curve, CurveKey, FitResult, ScanMeta

__all__ = [
    "Curve",
    "CurveKey",
    "FitResult",
    "ScanMeta",
    "parse_afm_text",
    "sliding_window_fit",
    "features",
]
