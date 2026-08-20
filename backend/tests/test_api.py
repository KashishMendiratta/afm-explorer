def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_upload_scan(client):
    with open(_sample_path(), "rb") as f:
        resp = client.post("/api/scans", files={"file": ("sample.txt", f, "text/plain")})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["n_curves"] == 12
    assert body["n_series"] == 2
    assert "scan_id" in body


def test_list_and_get_scan(client, uploaded_scan_id):
    resp = client.get("/api/scans")
    assert resp.status_code == 200
    scans = resp.json()
    assert any(s["scan_id"] == uploaded_scan_id for s in scans)

    resp = client.get(f"/api/scans/{uploaded_scan_id}")
    assert resp.status_code == 200
    assert resp.json()["scan_id"] == uploaded_scan_id


def test_get_scan_404(client):
    resp = client.get("/api/scans/does-not-exist")
    assert resp.status_code == 404


def test_get_curve_and_heuristic_estimate(client, uploaded_scan_id):
    resp = client.get(f"/api/scans/{uploaded_scan_id}/curves/0/0/0")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["distance"]) == len(body["force"]) > 0

    resp = client.get(f"/api/scans/{uploaded_scan_id}/curves/0/0/0/estimate?method=heuristic")
    assert resp.status_code == 200
    fit = resp.json()
    assert fit["method"] == "heuristic"
    assert fit["start_index"] < fit["end_index"]


def test_ml_estimate_without_trained_model_returns_409(client, uploaded_scan_id):
    resp = client.get(f"/api/scans/{uploaded_scan_id}/curves/0/0/0/estimate?method=ml")
    assert resp.status_code == 409


def test_heightmap_and_stiffnessmap(client, uploaded_scan_id):
    resp = client.get(f"/api/scans/{uploaded_scan_id}/heightmap?series=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["m"] == len(body["values"])

    resp = client.get(f"/api/scans/{uploaded_scan_id}/stiffnessmap?series=0&method=heuristic")
    assert resp.status_code == 200


def test_label_and_train_roundtrip(client, uploaded_scan_id):
    # label every push curve's contact point using the heuristic's own
    # estimate as a stand-in ground truth, purely to exercise the
    # label -> train -> ml-estimate pipeline end-to-end in CI (real usage
    # expects a human to click the true contact point in the frontend).
    for i in range(6):
        est = client.get(f"/api/scans/{uploaded_scan_id}/curves/0/{i}/0/estimate?method=heuristic").json()
        resp = client.post(
            "/api/labels",
            json={
                "scan_id": uploaded_scan_id,
                "series": 0,
                "i": i,
                "j": 0,
                "contact_index": est["contact_index"],
            },
        )
        assert resp.status_code == 200

    resp = client.get(f"/api/labels?scan_id={uploaded_scan_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 6

    resp = client.post("/api/train", json={"scan_ids": [uploaded_scan_id]})
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    # BackgroundTasks in TestClient run synchronously before the response
    # context closes, so the job should already be done here.
    resp = client.get(f"/api/train/{job_id}")
    assert resp.status_code == 200
    status = resp.json()
    assert status["status"] in {"completed", "failed"}
    # 6 labeled curves is a tiny dataset; assert the pipeline *ran*
    # end-to-end rather than asserting on model quality.
    if status["status"] == "failed":
        raise AssertionError(f"training failed: {status['detail']}")

    resp = client.get("/api/models/active")
    assert resp.status_code == 200
    assert resp.json()["has_model"] is True


def _sample_path():
    from pathlib import Path

    return Path(__file__).resolve().parents[2] / "data" / "samples" / "sample.txt"
