"""MCP tool definitions for AFM Explorer.

Every tool is a thin wrapper around mcp_server.client.AFMClient, which
talks to the FastAPI backend over HTTP — this module contains no parsing,
estimation, or storage logic of its own, same "thin layer over the real
backend" discipline as the Streamlit frontend.

Read tools (list/browse scans, heatmaps, curves, labels, model metrics) are
always registered. Write tools (submit_label, upload_scan, train_model) are
registered only when AFM_MCP_READONLY is not set — set it to run a
read-only assistant against a shared/public deployment. Regardless of that
flag, actually calling a write tool against a backend that has AFM_API_KEY
set requires this server to be configured with the same key (AFM_API_KEY
env var here too) — see backend/app/core/config.py's Settings.api_key.
"""

from __future__ import annotations

import os

from fastmcp import FastMCP

from mcp_server.client import get_client

READONLY = os.environ.get("AFM_MCP_READONLY", "").strip().lower() in {"1", "true", "yes"}

mcp = FastMCP(
    name="afm-explorer",
    instructions=(
        "Tools for exploring Atomic Force Microscopy (AFM) force-spectroscopy scans "
        "processed by the AFM Explorer backend. A scan is a grid of pixels; at each "
        "pixel a 'push' (series=0) and 'retract' (series=1) force-distance curve was "
        "recorded. The 'contact point' is where the curve transitions from flat/noisy "
        "to linear as the tip touches the sample; its slope is the stiffness at that "
        "pixel. Estimates come from a classical heuristic (always available) or a "
        "trained ML model ('method=ml', only available after train_model has been run "
        "and completed). Start with list_scans to find a scan_id, then get_height_map "
        "/ get_stiffness_map for an overview, or get_curve / get_contact_point_estimate "
        "to look at one pixel in detail."
    ),
)


def _summarize_grid(values: list[list[float | None]]) -> dict:
    """Reduce a (potentially 128x128 = 16k-cell) heatmap to summary
    statistics, since dumping the full grid into an LLM's context is
    usually not what's wanted. Includes *where* the min/max are, since
    "which pixel is stiffest" is the single most common question this is
    built to answer."""
    m = len(values)
    n = len(values[0]) if m else 0
    found = [(v, i, j) for i, row in enumerate(values) for j, v in enumerate(row) if v is not None]
    if not found:
        return {"m": m, "n": n, "count_valid": 0, "count_missing": m * n}

    vals = [v for v, _, _ in found]
    min_v, min_i, min_j = min(found, key=lambda t: t[0])
    max_v, max_i, max_j = max(found, key=lambda t: t[0])
    return {
        "m": m,
        "n": n,
        "count_valid": len(found),
        "count_missing": m * n - len(found),
        "min": min_v,
        "min_at": {"i": min_i, "j": min_j},
        "max": max_v,
        "max_at": {"i": max_i, "j": max_j},
        "mean": sum(vals) / len(vals),
    }


# --- read tools -------------------------------------------------------


@mcp.tool
async def list_scans() -> list[dict]:
    """List every uploaded AFM scan with its grid size, series count, and
    header metadata (spring constant, source filename)."""
    return await get_client().list_scans()


@mcp.tool
async def get_scan(scan_id: str) -> dict:
    """Get metadata for one scan by id (grid size, spring constant, units, etc.)."""
    return await get_client().get_scan(scan_id)


@mcp.tool
async def get_height_map(scan_id: str, series: int = 0, summarize: bool = True) -> dict:
    """Get the (approximate) height/topography map for a scan. summarize=True
    (default) returns compact statistics — min/max/mean and the (i, j) pixel
    where each extreme occurs — instead of the full grid; pass
    summarize=False for the raw per-pixel values."""
    result = await get_client().get_heightmap(scan_id, series)
    if not summarize:
        return result
    return {k: result[k] for k in ("scan_id", "series", "kind", "m", "n")} | {
        "summary": _summarize_grid(result["values"])
    }


@mcp.tool
async def get_stiffness_map(
    scan_id: str, series: int = 0, method: str = "heuristic", summarize: bool = True
) -> dict:
    """Get the stiffness (slope) map for a scan. method is 'heuristic'
    (always available) or 'ml' (requires a trained model — see
    get_active_model / train_model). summarize=True (default) returns
    compact statistics instead of the full grid — see get_height_map."""
    result = await get_client().get_stiffnessmap(scan_id, series, method)
    if not summarize:
        return result
    return {k: result[k] for k in ("scan_id", "series", "kind", "method", "m", "n")} | {
        "summary": _summarize_grid(result["values"])
    }


@mcp.tool
async def get_curve(scan_id: str, series: int, i: int, j: int) -> dict:
    """Get the raw (distance, force) arrays for one force curve."""
    return await get_client().get_curve(scan_id, series, i, j)


@mcp.tool
async def get_contact_point_estimate(
    scan_id: str, series: int, i: int, j: int, method: str = "heuristic"
) -> dict:
    """Get the estimated contact point / slope for one curve. method is
    'heuristic' (always available) or 'ml' (requires a trained model)."""
    return await get_client().get_estimate(scan_id, series, i, j, method)


@mcp.tool
async def list_labels(scan_id: str | None = None) -> list[dict]:
    """List saved human-labeled contact points, optionally filtered to one scan."""
    return await get_client().list_labels(scan_id)


@mcp.tool
async def get_active_model() -> dict:
    """Get the currently active trained ML model's version and metrics
    (window classification F1/precision/recall, and the baseline-vs-ML
    evaluation report if one exists), or has_model=False if none is trained yet."""
    return await get_client().get_active_model()


@mcp.tool
async def get_training_status(job_id: str) -> dict:
    """Poll the status of a training job started by train_model."""
    return await get_client().get_train_status(job_id)


# --- write tools (registered only when not read-only) ------------------

if not READONLY:

    @mcp.tool
    async def submit_label(scan_id: str, series: int, i: int, j: int, contact_index: int) -> dict:
        """Record a confirmed contact-point index for one curve — this
        becomes training data for the ML model via train_model. Only
        submit a contact_index you're confident is correct (e.g. one a
        human confirmed, or one you verified carefully against the raw
        curve via get_curve) — bad labels degrade the trained model, and
        there's no undo endpoint; a later correct label for the same curve
        does override the earlier one."""
        return await get_client().submit_label(scan_id, series, i, j, contact_index)

    @mcp.tool
    async def upload_scan(file_path: str) -> dict:
        """Upload and parse a raw AFM .txt export from a local file path
        on the machine running this MCP server (not a path on any remote
        deployment)."""
        return await get_client().upload_scan_file(file_path)

    @mcp.tool
    async def train_model(scan_ids: list[str] | None = None) -> dict:
        """Start training the ML contact-point model (+ an unsupervised
        quality-control model) using every saved label, optionally
        restricted to specific scan_ids. Returns a job_id — poll it with
        get_training_status. Training itself is typically fast (seconds to
        low tens of seconds); needs labels on at least 2 distinct curves."""
        return await get_client().train(scan_ids)
