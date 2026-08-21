import sys
from pathlib import Path

import httpx
import pytest
from mcp_server import client as mcp_client

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_TXT = REPO_ROOT / "data" / "samples" / "sample.txt"

# These tests exercise the real backend in-process (see afm_client below),
# but backend/app isn't an installed package (it's normally run via
# `uvicorn` from within backend/, same as backend/tests does) — add it to
# sys.path so `from app.main import app` resolves here too.
_BACKEND_DIR = str(REPO_ROOT / "backend")
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)


@pytest.fixture
async def afm_client(tmp_path, monkeypatch):
    """An AFMClient backed by an in-process ASGI transport against the real
    FastAPI backend app — no network, no separate server process, but
    genuine integration coverage of the HTTP contract between the two."""
    monkeypatch.setenv("AFM_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("AFM_API_KEY", raising=False)

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.main import app as backend_app

    transport = httpx.ASGITransport(app=backend_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield mcp_client.AFMClient(http)

    get_settings.cache_clear()


@pytest.fixture
async def uploaded_scan_id(afm_client) -> str:
    result = await afm_client.upload_scan_file(str(SAMPLE_TXT))
    return result["scan_id"]


@pytest.fixture
async def mcp_client_bound(afm_client):
    """Points server.py's tools at afm_client for the duration of the test
    (server.py's tools call mcp_server.client.get_client() internally)."""
    mcp_client.set_client(afm_client)
    yield
    mcp_client.set_client(None)
