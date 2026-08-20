import numpy as np
import plotly.graph_objects as go
import streamlit as st
from lib import api_client
from lib.scan_picker import pick_scan

st.set_page_config(page_title="Label Contact Points", page_icon="🏷️", layout="wide")
st.title("🏷️ Label Contact Points")
st.write(
    "Click on the curve where the tip first touches the surface (the start of the "
    "steep, roughly-linear region). Each label you add here becomes training data "
    "for the ML contact-point model — see the **Model Training & Metrics** page."
)

scan = pick_scan()
if scan is None:
    st.stop()

series = st.sidebar.selectbox(
    "Series", list(range(scan["n_series"])), format_func=lambda s: "push" if s == 0 else "retract"
)
i = st.sidebar.slider("i", 0, scan["m"] - 1, 0)
j = st.sidebar.slider("j", 0, scan["n"] - 1, 0)

curve = api_client.get_curve(scan["scan_id"], series, i, j)
d, f = curve["distance"], curve["force"]
n = len(d)

existing = [
    lbl for lbl in api_client.get_labels(scan["scan_id"]) if lbl["series"] == series and lbl["i"] == i and lbl["j"] == j
]
existing_index = existing[0]["contact_index"] if existing else None

fig = go.Figure()
fig.add_trace(go.Scatter(x=d, y=f, mode="lines+markers", marker=dict(size=4), name="curve"))
if existing_index is not None:
    fig.add_vline(x=d[existing_index], line=dict(color="green", dash="dot"), annotation_text="saved label")
fig.update_layout(
    title=f"Click the contact point — (i={i}, j={j}, series={series})",
    xaxis_title="distance (m)",
    yaxis_title="force (N)",
    height=520,
    clickmode="event+select",
)

# Streamlit's native chart click-capture (on_select) requires a reasonably
# recent Streamlit version; if it's unavailable in your installed version,
# use the numeric fallback below instead.
click_index = None
try:
    event = st.plotly_chart(fig, width='stretch', on_select="rerun", key=f"label_chart_{series}_{i}_{j}")
    points = event.selection.get("points", []) if event and hasattr(event, "selection") else []
    if points:
        clicked_x = points[0]["x"]
        click_index = int(np.argmin(np.abs(np.array(d) - clicked_x)))
except TypeError:
    # older Streamlit without on_select support
    st.plotly_chart(fig, width='stretch')
    st.caption("Your Streamlit version doesn't support click-to-select — use the slider below instead.")

st.subheader("Confirm contact-point index")
default_index = click_index if click_index is not None else (existing_index if existing_index is not None else n // 2)
chosen_index = st.slider("Contact-point index", 0, n - 1, int(default_index))
st.write(f"distance = `{d[chosen_index]:.6g} m`, force = `{f[chosen_index]:.6g} N`")

if st.button("💾 Save label", type="primary"):
    api_client.post_label(scan["scan_id"], series, i, j, chosen_index)
    st.success(f"Saved label at index {chosen_index} for (series={series}, i={i}, j={j}).")
    st.rerun()

st.divider()
all_labels = api_client.get_labels(scan["scan_id"])
st.caption(f"{len(all_labels)} labeled curve(s) so far in this scan.")
if all_labels:
    st.dataframe(all_labels, width='stretch', hide_index=True)
