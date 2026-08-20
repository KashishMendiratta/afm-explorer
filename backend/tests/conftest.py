from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_TXT = REPO_ROOT / "data" / "samples" / "sample.txt"


@pytest.fixture
def client(tmp_path, monkeypatch):
    # point the app at an isolated tmp data dir so tests never touch (or
    # depend on) real data, and each test run starts clean
    monkeypatch.setenv("AFM_DATA_DIR", str(tmp_path / "data"))

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import app

    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()


@pytest.fixture
def uploaded_scan_id(client):
    with open(SAMPLE_TXT, "rb") as f:
        resp = client.post("/api/scans", files={"file": ("sample.txt", f, "text/plain")})
    assert resp.status_code == 200, resp.text
    return resp.json()["scan_id"]
