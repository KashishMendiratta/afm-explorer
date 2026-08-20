import streamlit as st

from lib import api_client


def pick_scan() -> dict | None:
    """Sidebar scan selector shared by every page. Returns the full scan
    summary dict, or None if no scans exist yet."""
    scans = api_client.list_scans()
    if not scans:
        st.warning("No scans uploaded yet — go to the Home page first.")
        return None

    ids = [s["scan_id"] for s in scans]
    default = st.session_state.get("scan_id")
    index = ids.index(default) if default in ids else 0

    scan_id = st.sidebar.selectbox(
        "Scan",
        ids,
        index=index,
        format_func=lambda sid: next(s["source_filename"] for s in scans if s["scan_id"] == sid),
    )
    st.session_state["scan_id"] = scan_id
    return next(s for s in scans if s["scan_id"] == scan_id)
