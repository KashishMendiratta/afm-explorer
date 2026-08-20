import numpy as np
import pytest
from afm_core.preprocessing import build_scan_cache
from afm_core.schemas import Curve, CurveKey, Label, ScanMeta


def make_synthetic_curve(true_contact_index, n=300, slope=2.0, noise=0.02, seed=0):
    rng = np.random.default_rng(seed)
    d = np.linspace(0, 1, n)
    f = np.empty(n)
    f[:true_contact_index] = rng.normal(0, noise, true_contact_index)
    f[true_contact_index:] = slope * (d[true_contact_index:] - d[true_contact_index]) + rng.normal(
        0, noise / 5, n - true_contact_index
    )
    return d, f


@pytest.fixture
def synthetic_scan_and_labels():
    """A synthetic 'scan' of N curves, each with a known contact index, so
    the ML pipeline can be tested end-to-end without needing real
    hand-labeled AFM data."""
    scan_id = "synthetic-scan"
    curves = {}
    labels = []

    n_curves = 24
    for idx in range(n_curves):
        contact_index = 120 + (idx % 5) * 10  # varies a bit, deterministic
        d, f = make_synthetic_curve(contact_index, seed=idx)
        key = CurveKey(series=0, i=idx, j=0)
        curves[key.as_tuple()] = Curve(key=key, distance=d, force=f)
        labels.append(Label(scan_id=scan_id, key=key, contact_index=contact_index))

    meta = ScanMeta(source_filename="synthetic.txt", i_length=n_curves, j_length=1)
    cache = build_scan_cache(curves, meta)
    return {scan_id: cache}, labels
