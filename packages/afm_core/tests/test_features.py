import numpy as np
import pytest
from afm_core.features import (
    CURVE_FEATURE_NAMES,
    WINDOW_FEATURE_NAMES,
    curve_features,
    window_features,
)


def test_window_features_shape_and_names_match():
    d = np.linspace(0, 1, 60)
    f = 2.0 * d + np.random.default_rng(0).normal(0, 0.01, 60)
    feats = window_features(d, f, start=10, end=40, n_total=60)
    assert len(feats) == len(WINDOW_FEATURE_NAMES)
    assert all(np.isfinite(v) for v in feats)


def test_window_features_high_r_squared_on_clean_line():
    d = np.linspace(0, 1, 60)
    f = 2.0 * d + 0.5  # perfectly linear, no noise
    feats = window_features(d, f, start=0, end=60, n_total=60)
    r_squared = feats[WINDOW_FEATURE_NAMES.index("r_squared")]
    assert r_squared == pytest.approx(1.0, abs=1e-6)


def test_curve_features_shape_and_names_match():
    d = np.linspace(0, 1, 100)
    f = np.sin(d * 3) + np.random.default_rng(1).normal(0, 0.05, 100)
    feats = curve_features(d, f)
    assert len(feats) == len(CURVE_FEATURE_NAMES)
    assert all(np.isfinite(v) for v in feats)


def test_curve_features_flags_monotonicity_violation():
    # d goes up then briefly backwards -> some violation fraction > 0
    d = np.concatenate([np.linspace(0, 1, 50), np.linspace(0.95, 0.99, 5), np.linspace(1, 2, 45)])
    f = np.zeros_like(d)
    feats = curve_features(d, f)
    idx = CURVE_FEATURE_NAMES.index("monotonic_violation_frac")
    assert feats[idx] > 0
