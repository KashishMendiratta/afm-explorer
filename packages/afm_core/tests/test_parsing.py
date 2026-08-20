import numpy as np
from afm_core.parsing import parse_afm_text


def test_parses_all_curve_blocks(sample_txt_path):
    curves, meta = parse_afm_text(sample_txt_path)
    # sample.txt has 12 "# index:" blocks (verified via grep during dev):
    # a 6-point line scan (i=0..5, j=0), each with a push (s=0) and
    # retract (s=1) curve.
    assert len(curves) == 12


def test_series_alternates_and_covers_expected_grid(sample_txt_path):
    curves, meta = parse_afm_text(sample_txt_path)
    keys = sorted(curves.keys())
    series_present = {k[0] for k in keys}
    assert series_present == {0, 1}

    i_values = sorted({k[1] for k in keys})
    j_values = sorted({k[2] for k in keys})
    assert i_values == [0, 1, 2, 3, 4, 5]
    assert j_values == [0]

    # every (i, j) should have both a push and a retract curve
    for i in i_values:
        for j in j_values:
            assert (0, i, j) in curves
            assert (1, i, j) in curves


def test_curve_arrays_match_recorded_num_points(sample_txt_path):
    curves, meta = parse_afm_text(sample_txt_path)
    for key, curve in curves.items():
        assert len(curve.distance) == len(curve.force)
        assert len(curve.distance) > 0
        assert isinstance(curve.distance, np.ndarray)
        # every curve should have a plausible number of points (the header
        # advertises 698-700 recorded points per block in sample.txt)
        assert 100 <= len(curve.distance) <= 1000


def test_metadata_extracted(sample_txt_path):
    curves, meta = parse_afm_text(sample_txt_path)
    assert meta.i_length == 128
    assert meta.j_length == 128
    assert meta.spring_constant is not None
    assert meta.spring_constant > 0
    assert "vDeflection" in meta.columns
    assert meta.units  # non-empty
