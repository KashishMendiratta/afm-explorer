import numpy as np
import pytest
from afm_core.heuristics import all_windows, sliding_window_fit
from afm_core.parsing import parse_afm_text


def _synthetic_curve(true_slope=2.0, n=200, noise_std=0.02, seed=0):
    """A curve with a noisy flat 'approach' region followed by a clean
    linear 'contact' region, mimicking real AFM force curves."""
    rng = np.random.default_rng(seed)
    d = np.linspace(0, 1, n)

    flat_len = n // 2
    f = np.empty(n)
    f[:flat_len] = rng.normal(0, noise_std, flat_len)
    f[flat_len:] = true_slope * (d[flat_len:] - d[flat_len]) + rng.normal(
        0, noise_std / 5, n - flat_len
    )
    return d, f, flat_len


def test_recovers_known_slope_on_synthetic_curve():
    d, f, flat_len = _synthetic_curve(true_slope=3.5)
    fit = sliding_window_fit(d, f, window_size=30, step=5)

    assert fit.slope == pytest.approx(3.5, abs=0.5)
    # the fitted window should fall within (or very close to) the clean
    # linear region, not the noisy flat region
    assert fit.start_index >= flat_len - 30


def test_raises_on_curve_shorter_than_window():
    d = np.linspace(0, 1, 10)
    f = np.zeros(10)
    with pytest.raises(ValueError):
        sliding_window_fit(d, f, window_size=50)


def test_smoke_on_real_sample_curve(sample_txt_path):
    curves, _ = parse_afm_text(sample_txt_path)
    # pick any push curve
    key = next(k for k in curves if k[0] == 0)
    curve = curves[key]
    fit = sliding_window_fit(curve.distance, curve.force)
    assert np.isfinite(fit.slope)
    assert 0 <= fit.start_index < fit.end_index <= len(curve.distance)


def test_all_windows_covers_curve_without_exceeding_bounds():
    windows = list(all_windows(n_points=105, window_size=50, step=10))
    assert windows[0] == (0, 50)
    assert all(end <= 105 for _, end in windows)
    assert all(end - start == 50 for start, end in windows)
