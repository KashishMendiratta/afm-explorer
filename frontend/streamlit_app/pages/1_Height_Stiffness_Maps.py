import numpy as np
import plotly.graph_objects as go
import streamlit as st
from lib import api_client
from lib.scan_picker import pick_scan

st.set_page_config(page_title="Height & Stiffness Maps", page_icon="🗺️", layout="wide")
st.title("🗺️ Height & Stiffness Maps")

scan = pick_scan()
if scan is None:
    st.stop()

series = st.sidebar.selectbox("Series", list(range(scan["n_series"])), format_func=lambda s: "push" if s == 0 else "retract")
method = st.sidebar.radio("Stiffness estimator", ["heuristic", "ml"], horizontal=True)


def _heatmap(values, title, colorbar_title):
    z = np.array(values, dtype=float)
    fig = go.Figure(data=go.Heatmap(z=z, colorscale="Turbo", colorbar=dict(title=colorbar_title)))
    fig.update_layout(title=title, height=480, yaxis=dict(autorange="reversed"))
    return fig


col1, col2 = st.columns(2)

with col1:
    st.subheader("Height (derived topography)")
    heightmap = api_client.get_heightmap(scan["scan_id"], series)
    st.plotly_chart(_heatmap(heightmap["values"], "Height", "m"), width='stretch')
    st.caption(
        "Height is approximated as the distance at the estimated contact point of each "
        "push curve — this project doesn't have the instrument's separate topography channel."
    )

with col2:
    st.subheader(f"Stiffness ({method})")
    stiffnessmap = api_client.get_stiffnessmap(scan["scan_id"], series, method)
    if stiffnessmap is None:
        st.info("No trained ML model yet. Train one on the **Model Training & Metrics** page, or switch to `heuristic`.")
    else:
        st.plotly_chart(_heatmap(stiffnessmap["values"], "Stiffness (slope)", "N/m"), width='stretch')
