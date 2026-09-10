import sys
from pathlib import Path

STREAMLIT_APP = Path(__file__).resolve().parents[1] / "streamlit_app"
sys.path.insert(0, str(STREAMLIT_APP))

from lib.scan_picker import coordinate_options  # noqa: E402


def test_coordinate_options_never_invent_sparse_grid_locations():
    coordinates = [
        {"series": 0, "i": 2, "j": 7},
        {"series": 0, "i": 9, "j": 1},
        {"series": 0, "i": 9, "j": 4},
        {"series": 1, "i": 5, "j": 3},
    ]
    assert coordinate_options(coordinates, 0) == ([2, 9], [7])
    assert coordinate_options(coordinates, 0, i=9) == ([2, 9], [1, 4])
    assert coordinate_options(coordinates, 1, i=5) == ([5], [3])
