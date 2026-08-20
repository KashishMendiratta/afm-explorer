import streamlit as st
from lib import api_client

st.set_page_config(page_title="AFM Explorer", page_icon="🔬", layout="wide")

st.title("🔬 AFM Explorer")
st.write(
    "Upload an AFM force-spectroscopy text export to parse it, browse the "
    "height/stiffness maps, inspect individual force curves, label contact "
    "points, and train the contact-point ML model."
)

if not api_client.backend_healthy():
    st.error(
        f"Can't reach the backend API at `{api_client.BACKEND_URL}`. "
        "Make sure it's running (see docker-compose or `uvicorn app.main:app`)."
    )
    st.stop()

st.subheader("Upload a scan")
uploaded = st.file_uploader("AFM text export (.txt)", type=["txt"])
if uploaded is not None and st.button("Parse & upload"):
    with st.spinner("Parsing..."):
        result = api_client.upload_scan(uploaded.name, uploaded.getvalue())
    api_client.list_scans.clear()
    st.success(
        f"Parsed **{result['n_curves']}** curves into a **{result['m']}×{result['n']}** grid "
        f"({result['n_series']} series). Scan id: `{result['scan_id']}`"
    )
    st.session_state["scan_id"] = result["scan_id"]

st.subheader("Existing scans")
scans = api_client.list_scans()
if not scans:
    st.info("No scans uploaded yet.")
else:
    for s in scans:
        cols = st.columns([3, 1, 1, 1, 2])
        cols[0].markdown(f"`{s['scan_id']}`  —  *{s['source_filename']}*")
        cols[1].write(f"{s['m']}×{s['n']}")
        cols[2].write(f"{s['n_series']} series")
        cols[3].write(f"k={s['meta']['spring_constant']:.4g}" if s["meta"]["spring_constant"] else "—")
        if cols[4].button("Open", key=f"open-{s['scan_id']}"):
            st.session_state["scan_id"] = s["scan_id"]
            st.success(f"Selected scan `{s['scan_id']}` — use the pages in the sidebar.")

st.divider()
active_model = api_client.get_active_model()
if active_model["has_model"]:
    st.caption(f"✅ Active ML model: `{active_model['version']}`")
else:
    st.caption("ℹ️ No ML model trained yet — label some curves and train one on the Model page.")
