"""Thin async HTTP client for the AFM Explorer backend — the only module in
this package that knows the backend's URLs. server.py's tools call this and
otherwise contain no HTTP details, mirroring the same "thin client, backend
is the source of truth" discipline as frontend/streamlit_app/lib/api_client.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

DEFAULT_BACKEND_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 30.0


class AFMAPIError(RuntimeError):
    """Raised with a message suitable for showing an LLM/agent directly —
    prefers the backend's own {"detail": "..."} body over a raw status
    line, since that's usually the actionable part (e.g. "no trained ML
    model is available yet — POST /api/train first")."""


def _raise_for_status(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    detail = resp.text
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            detail = body["detail"]
    except ValueError:
        pass
    raise AFMAPIError(f"{resp.request.method} {resp.request.url} -> {resp.status_code}: {detail}")


class AFMClient:
    """Wraps an httpx.AsyncClient already pointed at the backend (base_url
    set). Tests inject one backed by an ASGI transport against the FastAPI
    app in-process; real usage gets one pointed at BACKEND_URL over the
    network — see get_client() below."""

    def __init__(self, http: httpx.AsyncClient, api_key: str | None = None):
        self._http = http
        self._api_key = api_key

    def _write_headers(self) -> dict[str, str]:
        return {"X-API-Key": self._api_key} if self._api_key else {}

    async def health(self) -> dict:
        resp = await self._http.get("/api/health")
        _raise_for_status(resp)
        return resp.json()

    async def list_scans(self) -> list[dict]:
        resp = await self._http.get("/api/scans")
        _raise_for_status(resp)
        return resp.json()

    async def get_scan(self, scan_id: str) -> dict:
        resp = await self._http.get(f"/api/scans/{scan_id}")
        _raise_for_status(resp)
        return resp.json()

    async def upload_scan_bytes(self, filename: str, content: bytes) -> dict:
        resp = await self._http.post(
            "/api/scans",
            files={"file": (filename, content, "text/plain")},
            headers=self._write_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def upload_scan_file(self, path: str) -> dict:
        p = Path(path).expanduser()
        if not p.is_file():
            raise AFMAPIError(f"no such file: {p}")
        return await self.upload_scan_bytes(p.name, p.read_bytes())

    async def get_heightmap(self, scan_id: str, series: int = 0) -> dict:
        resp = await self._http.get(f"/api/scans/{scan_id}/heightmap", params={"series": series})
        _raise_for_status(resp)
        return resp.json()

    async def get_stiffnessmap(self, scan_id: str, series: int = 0, method: str = "heuristic") -> dict:
        resp = await self._http.get(
            f"/api/scans/{scan_id}/stiffnessmap", params={"series": series, "method": method}
        )
        _raise_for_status(resp)
        return resp.json()

    async def get_curve(self, scan_id: str, series: int, i: int, j: int) -> dict:
        resp = await self._http.get(f"/api/scans/{scan_id}/curves/{series}/{i}/{j}")
        _raise_for_status(resp)
        return resp.json()

    async def get_estimate(self, scan_id: str, series: int, i: int, j: int, method: str = "heuristic") -> dict:
        resp = await self._http.get(
            f"/api/scans/{scan_id}/curves/{series}/{i}/{j}/estimate", params={"method": method}
        )
        _raise_for_status(resp)
        return resp.json()

    async def list_labels(self, scan_id: str | None = None) -> list[dict]:
        resp = await self._http.get("/api/labels", params={"scan_id": scan_id} if scan_id else {})
        _raise_for_status(resp)
        return resp.json()

    async def submit_label(self, scan_id: str, series: int, i: int, j: int, contact_index: int) -> dict:
        resp = await self._http.post(
            "/api/labels",
            json={"scan_id": scan_id, "series": series, "i": i, "j": j, "contact_index": contact_index},
            headers=self._write_headers(),
        )
        _raise_for_status(resp)
        return resp.json()

    async def train(self, scan_ids: list[str] | None = None) -> dict:
        resp = await self._http.post(
            "/api/train", json={"scan_ids": scan_ids}, headers=self._write_headers()
        )
        _raise_for_status(resp)
        return resp.json()

    async def get_train_status(self, job_id: str) -> dict:
        resp = await self._http.get(f"/api/train/{job_id}")
        _raise_for_status(resp)
        return resp.json()

    async def get_active_model(self) -> dict:
        resp = await self._http.get("/api/models/active")
        _raise_for_status(resp)
        return resp.json()


_client: AFMClient | None = None


def get_client() -> AFMClient:
    """Default client for real (non-test) usage: reads BACKEND_URL /
    AFM_API_KEY from the environment, same convention as the Streamlit
    frontend and the backend itself. Cached as a singleton so the
    underlying connection pool is reused across tool calls."""
    global _client
    if _client is None:
        base_url = os.environ.get("BACKEND_URL", DEFAULT_BACKEND_URL)
        api_key = os.environ.get("AFM_API_KEY")
        http = httpx.AsyncClient(base_url=base_url, timeout=DEFAULT_TIMEOUT)
        _client = AFMClient(http, api_key=api_key)
    return _client


def set_client(client: AFMClient | None) -> None:
    """Test hook: inject (or reset, with None) the singleton so server.py's
    tools — which call get_client() internally — exercise a client backed
    by an in-process ASGI transport instead of a real network call."""
    global _client
    _client = client
