import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_SOURCE = REPO_ROOT / "data" / "samples" / "sample.txt"


@pytest.fixture
def sample_txt_path(tmp_path) -> Path:
    """Copy the committed sample fixture into a tmp dir so tests don't
    depend on cwd."""
    dest = tmp_path / "sample.txt"
    shutil.copy(SAMPLE_SOURCE, dest)
    return dest
