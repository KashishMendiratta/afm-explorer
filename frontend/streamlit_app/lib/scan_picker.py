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


def coordinate_options(coordinates: list[dict], series: int, i: int | None = None) -> tuple[list[int], list[int]]:
    """Return actual i values and the actual j values for one selected i."""
    i_values = sorted({item["i"] for item in coordinates if item["series"] == series})
    selected_i = i if i in i_values else (i_values[0] if i_values else None)
    j_values = sorted(
        {
            item["j"]
            for item in coordinates
            if item["series"] == series and item["i"] == selected_i
        }
    )
    return i_values, j_values


def pick_curve_coordinate(scan: dict) -> tuple[int, int, int] | None:
    """Sidebar picker constrained to curves actually present in a scan."""
    coordinates = api_client.get_curve_coordinates(scan["scan_id"])
    if not coordinates:
        st.warning("This scan contains no usable force curves.")
        return None

    series_values = sorted({item["series"] for item in coordinates})
    series = st.sidebar.selectbox(
        "Series",
        series_values,
        format_func=lambda value: "push" if value == 0 else "retract" if value == 1 else f"series {value}",
    )
    i_values, _ = coordinate_options(coordinates, series)
    i = st.sidebar.select_slider("i (available)", options=i_values)
    _, j_values = coordinate_options(coordinates, series, i)
    j = st.sidebar.select_slider("j (available)", options=j_values)
    st.sidebar.caption(
        f"Showing only measured locations ({sum(item['series'] == series for item in coordinates)} available)."
    )
    return series, i, j
