"""Thin HTTP client for the FastAPI backend. No business logic lives here —
every function is a direct wrapper around one backend endpoint, so the
Streamlit pages stay presentation-only and the backend stays the single
source of truth for parsing/estimation/ML logic.
"""

from __future__ import annotations

import os

import requests
import streamlit as st

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
TIMEOUT = 30


def _url(path: str) -> str:
    return f"{BACKEND_URL.rstrip('/')}{path}"


def upload_scan(filename: str, content: bytes) -> dict:
    resp = requests.post(
        _url("/api/scans"),
        files={"file": (filename, content, "text/plain")},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def list_scans() -> list[dict]:
    resp = requests.get(_url("/api/scans"), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=30)
def get_scan(scan_id: str) -> dict:
    resp = requests.get(_url(f"/api/scans/{scan_id}"), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=60)
def get_heightmap(scan_id: str, series: int) -> dict:
    resp = requests.get(_url(f"/api/scans/{scan_id}/heightmap"), params={"series": series}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=60)
def get_stiffnessmap(scan_id: str, series: int, method: str) -> dict | None:
    resp = requests.get(
        _url(f"/api/scans/{scan_id}/stiffnessmap"),
        params={"series": series, "method": method},
        timeout=TIMEOUT,
    )
    if resp.status_code == 409:
        return None  # no trained ML model yet
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=60)
def get_curve(scan_id: str, series: int, i: int, j: int) -> dict:
    resp = requests.get(_url(f"/api/scans/{scan_id}/curves/{series}/{i}/{j}"), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


@st.cache_data(ttl=60)
def get_estimate(scan_id: str, series: int, i: int, j: int, method: str) -> dict | None:
    resp = requests.get(
        _url(f"/api/scans/{scan_id}/curves/{series}/{i}/{j}/estimate"),
        params={"method": method},
        timeout=TIMEOUT,
    )
    if resp.status_code == 409:
        return None
    resp.raise_for_status()
    return resp.json()


def post_label(scan_id: str, series: int, i: int, j: int, contact_index: int) -> dict:
    resp = requests.post(
        _url("/api/labels"),
        json={"scan_id": scan_id, "series": series, "i": i, "j": j, "contact_index": contact_index},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_labels(scan_id: str | None = None) -> list[dict]:
    params = {"scan_id": scan_id} if scan_id else {}
    resp = requests.get(_url("/api/labels"), params=params, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def post_train(scan_ids: list[str] | None = None) -> dict:
    resp = requests.post(_url("/api/train"), json={"scan_ids": scan_ids}, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_train_status(job_id: str) -> dict:
    resp = requests.get(_url(f"/api/train/{job_id}"), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def get_active_model() -> dict:
    resp = requests.get(_url("/api/models/active"), timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def backend_healthy() -> bool:
    try:
        resp = requests.get(_url("/api/health"), timeout=5)
        return resp.status_code == 200
    except requests.RequestException:
        return False
