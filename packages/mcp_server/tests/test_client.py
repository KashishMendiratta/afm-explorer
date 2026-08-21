"""Exercises AFMClient's wrapper methods against the real backend (via an
in-process ASGI transport, see conftest.py) — i.e. that our HTTP calls
actually match the backend's routes/params/response shapes, not just that
our own code is internally consistent."""

from pathlib import Path

from mcp_server.client import AFMAPIError

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_TXT = REPO_ROOT / "data" / "samples" / "sample.txt"


async def test_health(afm_client):
    assert await afm_client.health() == {"status": "ok"}


async def test_upload_and_list_and_get_scan(afm_client):
    result = await afm_client.upload_scan_file(str(SAMPLE_TXT))
    assert result["n_curves"] == 12
    scan_id = result["scan_id"]

    scans = await afm_client.list_scans()
    assert any(s["scan_id"] == scan_id for s in scans)

    scan = await afm_client.get_scan(scan_id)
    assert scan["scan_id"] == scan_id


async def test_upload_scan_file_missing_path_raises_readable_error(afm_client):
    try:
        await afm_client.upload_scan_file("/no/such/file.txt")
        raise AssertionError("expected AFMAPIError")
    except AFMAPIError as exc:
        assert "no such file" in str(exc)


async def test_curve_and_heuristic_estimate(afm_client, uploaded_scan_id):
    curve = await afm_client.get_curve(uploaded_scan_id, 0, 0, 0)
    assert len(curve["distance"]) == len(curve["force"]) > 0

    fit = await afm_client.get_estimate(uploaded_scan_id, 0, 0, 0, method="heuristic")
    assert fit["method"] == "heuristic"
    assert fit["start_index"] < fit["end_index"]


async def test_ml_estimate_without_trained_model_raises_readable_error(afm_client, uploaded_scan_id):
    try:
        await afm_client.get_estimate(uploaded_scan_id, 0, 0, 0, method="ml")
        raise AssertionError("expected AFMAPIError")
    except AFMAPIError as exc:
        assert "train" in str(exc).lower()


async def test_heightmap_and_stiffnessmap(afm_client, uploaded_scan_id):
    heightmap = await afm_client.get_heightmap(uploaded_scan_id, series=0)
    assert heightmap["m"] == len(heightmap["values"])

    stiffnessmap = await afm_client.get_stiffnessmap(uploaded_scan_id, series=0, method="heuristic")
    assert stiffnessmap["kind"] == "stiffness"


async def test_label_and_train_roundtrip(afm_client, uploaded_scan_id):
    for i in range(6):
        est = await afm_client.get_estimate(uploaded_scan_id, 0, i, 0, method="heuristic")
        saved = await afm_client.submit_label(uploaded_scan_id, 0, i, 0, est["contact_index"])
        assert saved["contact_index"] == est["contact_index"]

    labels = await afm_client.list_labels(uploaded_scan_id)
    assert len(labels) == 6

    job = await afm_client.train(scan_ids=[uploaded_scan_id])
    status = await afm_client.get_train_status(job["job_id"])
    assert status["status"] in {"completed", "failed", "pending", "running"}

    active = await afm_client.get_active_model()
    assert "has_model" in active
