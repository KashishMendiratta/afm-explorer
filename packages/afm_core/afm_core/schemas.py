"""Lightweight, dependency-free data structures shared across afm_core, ml,
and backend. Deliberately plain dataclasses (not pydantic) so this package
has no web-framework dependency and can be reused from CLI scripts, the ML
pipeline, and the API layer alike.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass(frozen=True, order=True)
class CurveKey:
    """Identifies one force-distance curve within a scan.

    series: 0 = extend/push, 1 = retract (alternates in the raw file).
    i, j: grid coordinates of the point on the sample surface.
    """

    series: int
    i: int
    j: int

    def as_tuple(self) -> tuple:
        return (self.series, self.i, self.j)

    def __str__(self) -> str:
        return f"s{self.series}-i{self.i:03d}-j{self.j:03d}"


@dataclass
class Curve:
    """One raw force-distance curve."""

    key: CurveKey
    distance: np.ndarray  # meters
    force: np.ndarray  # newtons (or proxy units, see ScanMeta.units)

    def __len__(self) -> int:
        return len(self.distance)


@dataclass
class ScanMeta:
    """Metadata parsed from the AFM text export header."""

    source_filename: str
    i_length: Optional[int] = None
    j_length: Optional[int] = None
    fast_size: Optional[float] = None
    slow_size: Optional[float] = None
    spring_constant: Optional[float] = None
    sensitivity: Optional[float] = None
    columns: list[str] = field(default_factory=list)
    units: list[str] = field(default_factory=list)
    n_series: int = 2


@dataclass
class FitResult:
    """Result of estimating the linear contact region of a curve."""

    slope: float
    intercept: float
    start_index: int
    end_index: int
    r_squared: float
    method: str  # "heuristic" or "ml"
    contact_index: Optional[int] = None  # midpoint / representative index

    def __post_init__(self) -> None:
        if self.contact_index is None:
            self.contact_index = (self.start_index + self.end_index) // 2


@dataclass
class Label:
    """A user-supplied ground-truth contact point for one curve."""

    scan_id: str
    key: CurveKey
    contact_index: int
    created_at: Optional[str] = None
