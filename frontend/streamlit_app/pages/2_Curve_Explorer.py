import plotly.graph_objects as go
import streamlit as st
from lib import api_client
from lib.scan_picker import pick_scan

st.set_page_config(page_title="Curve Explorer", page_icon="📈", layout="wide")
st.title("📈 Curve Explorer")

scan = pick_scan()
if scan is None:
    st.stop()

series = st.sidebar.selectbox("Series", list(range(scan["n_series"])), format_func=lambda s: "push" if s == 0 else "retract")
i = st.sidebar.slider("i", 0, scan["m"] - 1, 0)
j = st.sidebar.slider("j", 0, scan["n"] - 1, 0)

curve = api_client.get_curve(scan["scan_id"], series, i, j)
d, f = curve["distance"], curve["force"]

fig = go.Figure()
fig.add_trace(go.Scattergl(x=d, y=f, mode="markers", marker=dict(size=3), name="raw data"))

heuristic_fit = api_client.get_estimate(scan["scan_id"], series, i, j, "heuristic")
ml_fit = api_client.get_estimate(scan["scan_id"], series, i, j, "ml")

for fit, color, label in [(heuristic_fit, "red", "heuristic"), (ml_fit, "orange", "ml")]:
    if fit is None:
        continue
    x0, x1 = d[fit["start_index"]], d[fit["end_index"] - 1]
    y0 = fit["slope"] * x0 + fit["intercept"]
    y1 = fit["slope"] * x1 + fit["intercept"]
    fig.add_trace(
        go.Scatter(
            x=[x0, x1],
            y=[y0, y1],
            mode="lines+markers",
            line=dict(color=color, dash="dash"),
            name=f"{label} fit (slope={fit['slope']:.4g} N/m, R²={fit['r_squared']:.3f})",
        )
    )

fig.update_layout(
    title=f"{'push' if series == 0 else 'retract'} curve at (i={i}, j={j})",
    xaxis_title="distance (m)",
    yaxis_title="force (N)",
    height=560,
)
st.plotly_chart(fig, width='stretch')

cols = st.columns(2)
with cols[0]:
    st.markdown("**Classical heuristic**")
    st.json(heuristic_fit if heuristic_fit else {"status": "unavailable"})
with cols[1]:
    st.markdown("**ML model**")
    st.json(ml_fit if ml_fit else {"status": "no trained model yet"})
