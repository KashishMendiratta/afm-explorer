"""Parser for the custom AFM force-spectroscopy text export format.

This is a single, consolidated version of the parsing logic that used to be
copy-pasted (with small drifting differences) across estimate_afm.py,
plotafm.py, afm.py, and app2.py. Behavior matches the original scripts:

- Lines starting with '#' carry metadata.
- A line containing 'index:' starts a new curve block and alternates the
  series between 0 (extend/push) and 1 (retract).
- 'iIndex:' / 'jIndex:' give the grid coordinates of the point.
- 'recorded-num-points' marks the start of numeric data rows.
- Data rows are whitespace-separated floats; we keep the first two columns
  as (distance, force), matching the original scripts' use of
  'smoothedMeasuredHeight' and 'vDeflection' as (d, f).
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from afm_core.schemas import Curve, CurveKey, ScanMeta

logger = logging.getLogger(__name__)


def _try_float(value: str) -> float | None:
    try:
        return float(value)
    except ValueError:
        return None


def _try_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def parse_afm_text(source: str | Path) -> tuple[dict[tuple[int, int, int], Curve], ScanMeta]:
    """Parse an AFM text export.

    Parameters
    ----------
    source: path to the .txt file.

    Returns
    -------
    (curves, meta): curves is a dict keyed by (series, i, j) -> Curve;
    meta carries scan-level metadata parsed from the header.
    """
    path = Path(source)
    text = path.read_text()
    lines = text.splitlines()

    meta = ScanMeta(source_filename=path.name)
    curves: dict[tuple[int, int, int], Curve] = {}

    s: int | None = None
    i: int | None = None
    j: int | None = None
    d: list[float] = []
    f: list[float] = []
    collecting_data = False
    current_series = 0
    n_blocks_seen = 0

    def flush_block() -> None:
        if d and f and s is not None and i is not None and j is not None:
            key = CurveKey(s, i, j)
            curves[key.as_tuple()] = Curve(
                key=key,
                distance=np.array(d, dtype=np.float64),
                force=np.array(f, dtype=np.float64),
            )

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            # A new 'index:' line closes the previous block (if any) and
            # opens a new one, alternating series 0/1. Note: this does NOT
            # spuriously match 'iIndex:'/'jIndex:' lines because 'in' is a
            # case-sensitive substring check ('index:' != 'Index:').
            if "index:" in line:
                flush_block()
                d, f = [], []
                s = current_series
                current_series = (current_series + 1) % meta.n_series
                collecting_data = False
                n_blocks_seen += 1
            elif "iIndex:" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    parsed = _try_int(parts[1].strip())
                    if parsed is not None:
                        i = parsed
                    else:
                        logger.warning("could not parse iIndex from line: %s", line)
            elif "jIndex:" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    parsed = _try_int(parts[1].strip())
                    if parsed is not None:
                        j = parsed
                    else:
                        logger.warning("could not parse jIndex from line: %s", line)
            elif "recorded-num-points" in line:
                collecting_data = True
            elif line.startswith("# iLength:"):
                meta.i_length = _try_int(line.split(":")[-1].strip())
            elif line.startswith("# jLength:"):
                meta.j_length = _try_int(line.split(":")[-1].strip())
            elif line.startswith("# fastSize:"):
                meta.fast_size = _try_float(line.split(":")[-1].strip())
            elif line.startswith("# slowSize:"):
                meta.slow_size = _try_float(line.split(":")[-1].strip())
            elif line.startswith("# springConstant:"):
                meta.spring_constant = _try_float(line.split(":")[-1].strip())
            elif line.startswith("# sensitivity:"):
                meta.sensitivity = _try_float(line.split(":")[-1].strip())
            elif line.startswith("# columns:"):
                meta.columns = line.split(":", 1)[1].strip().split()
            elif line.startswith("# units:"):
                meta.units = line.split(":", 1)[1].strip().split()
        elif collecting_data:
            parts = line.split()
            if len(parts) >= 2:
                dv, fv = _try_float(parts[0]), _try_float(parts[1])
                if dv is not None and fv is not None:
                    d.append(dv)
                    f.append(fv)
                else:
                    logger.debug("skipping malformed data row: %s", line)

    flush_block()  # last block

    logger.info(
        "parsed %s: %d curve blocks, %d retained (i_length=%s, j_length=%s)",
        path.name,
        n_blocks_seen,
        len(curves),
        meta.i_length,
        meta.j_length,
    )
    return curves, meta
