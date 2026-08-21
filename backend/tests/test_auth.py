"""AFM_API_KEY is opt-in: unset (the default, exercised by every other test
via the `client` fixture) means write endpoints stay open, matching this
project's original unauthenticated behavior. These tests cover the
opt-in-enabled path specifically.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_TXT = REPO_ROOT / "data" / "samples" / "sample.txt"


@pytest.fixture
def client_with_api_key(tmp_path, monkeypatch):
    monkeypatch.setenv("AFM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("AFM_API_KEY", "s3cr3t")

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import app

    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()


def test_read_endpoints_unaffected_by_api_key(client_with_api_key):
    # GET endpoints never require the key, even when one is configured
    resp = client_with_api_key.get("/api/scans")
    assert resp.status_code == 200
    resp = client_with_api_key.get("/api/health")
    assert resp.status_code == 200


def test_upload_scan_requires_api_key(client_with_api_key):
    with open(SAMPLE_TXT, "rb") as f:
        resp = client_with_api_key.post("/api/scans", files={"file": ("sample.txt", f, "text/plain")})
    assert resp.status_code == 401

    with open(SAMPLE_TXT, "rb") as f:
        resp = client_with_api_key.post(
            "/api/scans",
            files={"file": ("sample.txt", f, "text/plain")},
            headers={"X-API-Key": "wrong"},
        )
    assert resp.status_code == 401

    with open(SAMPLE_TXT, "rb") as f:
        resp = client_with_api_key.post(
            "/api/scans",
            files={"file": ("sample.txt", f, "text/plain")},
            headers={"X-API-Key": "s3cr3t"},
        )
    assert resp.status_code == 200


def test_labels_and_train_require_api_key(client_with_api_key):
    resp = client_with_api_key.post(
        "/api/labels", json={"scan_id": "x", "series": 0, "i": 0, "j": 0, "contact_index": 0}
    )
    assert resp.status_code == 401

    resp = client_with_api_key.post("/api/train", json={})
    assert resp.status_code == 401

    resp = client_with_api_key.post("/api/train", json={}, headers={"X-API-Key": "s3cr3t"})
    assert resp.status_code == 200
