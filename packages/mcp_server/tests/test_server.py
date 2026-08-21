"""End-to-end: calls the actual MCP tools (via fastmcp's in-memory Client,
the standard way to test a FastMCP server) against the real backend, bound
through mcp_client_bound. This is the layer an LLM agent actually talks to,
so it's worth covering distinctly from test_client.py's lower-level checks."""

import importlib
import sys
from pathlib import Path

import pytest
from fastmcp import Client

REPO_ROOT = Path(__file__).resolve().parents[3]
SAMPLE_TXT = REPO_ROOT / "data" / "samples" / "sample.txt"


async def test_default_tool_set_includes_reads_and_writes(mcp_client_bound):
    from mcp_server.server import mcp

    async with Client(mcp) as client:
        tools = {t.name for t in await client.list_tools()}

    for name in ["list_scans", "get_scan", "get_height_map", "get_stiffness_map", "get_curve",
                 "get_contact_point_estimate", "list_labels", "get_active_model", "get_training_status"]:
        assert name in tools, f"missing read tool: {name}"
    for name in ["submit_label", "upload_scan", "train_model"]:
        assert name in tools, f"missing write tool: {name}"


async def test_readonly_mode_omits_write_tools(monkeypatch):
    monkeypatch.setenv("AFM_MCP_READONLY", "true")
    sys.modules.pop("mcp_server.server", None)
    server_module = importlib.import_module("mcp_server.server")
    try:
        async with Client(server_module.mcp) as client:
            tools = {t.name for t in await client.list_tools()}
        assert "list_scans" in tools
        for name in ["submit_label", "upload_scan", "train_model"]:
            assert name not in tools, f"write tool {name} should be omitted in readonly mode"
    finally:
        monkeypatch.delenv("AFM_MCP_READONLY", raising=False)
        sys.modules.pop("mcp_server.server", None)
        importlib.import_module("mcp_server.server")  # restore default (non-readonly) module state


async def test_list_scans_and_get_height_map_summary(mcp_client_bound, uploaded_scan_id):
    from mcp_server.server import mcp

    async with Client(mcp) as client:
        result = await client.call_tool("list_scans", {})
        scans = result.data
        assert any(s["scan_id"] == uploaded_scan_id for s in scans)

        result = await client.call_tool("get_height_map", {"scan_id": uploaded_scan_id})
        body = result.data
        assert "summary" in body
        assert body["summary"]["m"] == body["m"]
        assert "min_at" in body["summary"]


async def test_submit_label_and_train_via_tools(mcp_client_bound, uploaded_scan_id, afm_client):
    from mcp_server.server import mcp

    async with Client(mcp) as client:
        for i in range(6):
            est = await afm_client.get_estimate(uploaded_scan_id, 0, i, 0, method="heuristic")
            result = await client.call_tool(
                "submit_label",
                {
                    "scan_id": uploaded_scan_id,
                    "series": 0,
                    "i": i,
                    "j": 0,
                    "contact_index": est["contact_index"],
                },
            )
            assert result.data["contact_index"] == est["contact_index"]

        result = await client.call_tool("train_model", {"scan_ids": [uploaded_scan_id]})
        job_id = result.data["job_id"]

        result = await client.call_tool("get_training_status", {"job_id": job_id})
        assert result.data["status"] in {"completed", "failed", "pending", "running"}


async def test_get_contact_point_estimate_without_ml_model_surfaces_tool_error(
    mcp_client_bound, uploaded_scan_id
):
    from mcp_server.server import mcp

    async with Client(mcp) as client:
        with pytest.raises(Exception):  # fastmcp surfaces AFMAPIError as a ToolError
            await client.call_tool(
                "get_contact_point_estimate",
                {"scan_id": uploaded_scan_id, "series": 0, "i": 0, "j": 0, "method": "ml"},
            )
