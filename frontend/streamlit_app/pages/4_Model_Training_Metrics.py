import time

import streamlit as st
from lib import api_client

st.set_page_config(page_title="Model Training & Metrics", page_icon="🧠", layout="wide")
st.title("🧠 Model Training & Metrics")

st.write(
    "Trains the supervised contact-point classifier (gradient-boosted trees over "
    "windowed curve features) plus an unsupervised curve-quality model, using every "
    "label you've saved on the **Label Contact Points** page. Needs labels on at "
    "least a couple of distinct curves to produce a meaningful train/evaluation split."
)

all_labels = api_client.get_labels()
n_labeled_curves = len({(lbl["scan_id"], lbl["series"], lbl["i"], lbl["j"]) for lbl in all_labels})
st.metric("Total labeled curves (all scans)", n_labeled_curves)

if st.button("🚀 Train model", type="primary", disabled=n_labeled_curves < 2):
    job = api_client.post_train()
    job_id = job["job_id"]
    status_box = st.empty()
    with st.spinner("Training..."):
        for _ in range(60):
            status = api_client.get_train_status(job_id)
            status_box.write(f"Status: `{status['status']}`")
            if status["status"] in {"completed", "failed"}:
                break
            time.sleep(1)

    if status["status"] == "failed":
        st.error(f"Training failed: {status['detail']}")
    else:
        st.success(f"Trained model `{status['model_version']}`")
        st.session_state["last_train_metrics"] = status["metrics"]

if n_labeled_curves < 2:
    st.info("Label at least 2 curves (ideally dozens, across a few scans) before training.")

st.divider()
st.subheader("Active model")
active = api_client.get_active_model()
if not active["has_model"]:
    st.info("No model trained yet.")
else:
    st.write(f"Version: `{active['version']}`")
    metrics = active.get("metrics") or {}

    cols = st.columns(3)
    cols[0].metric("Window classification F1", f"{metrics.get('window_f1', float('nan')):.3f}")
    cols[1].metric("Precision", f"{metrics.get('window_precision', float('nan')):.3f}")
    cols[2].metric("Recall", f"{metrics.get('window_recall', float('nan')):.3f}")

    st.caption(f"Trained on {metrics.get('n_train_rows', '?')} window rows from {metrics.get('n_labeled_curves', '?')} labeled curves.")

    eval_report = metrics.get("evaluation") or {}
    if eval_report:
        st.subheader("Baseline (heuristic) vs. ML — held-out curves")
        st.write(
            "Mean absolute error between each estimator's predicted contact index and the "
            f"human-labeled ground truth, on {eval_report.get('n_eval_curves', 0)} held-out curve(s) "
            "not used for training."
        )
        cols = st.columns(2)
        cols[0].metric("Heuristic mean |error| (samples)", f"{eval_report.get('heuristic_mean_abs_error') or float('nan'):.1f}")
        cols[1].metric("ML mean |error| (samples)", f"{eval_report.get('ml_mean_abs_error') or float('nan'):.1f}")
    else:
        st.caption("No held-out evaluation curves yet — label more curves for a train/eval split.")

    st.caption(f"Quality-control (anomaly) model trained: {'yes' if metrics.get('has_qc_model') else 'no'}")

    with st.expander("Raw metrics JSON"):
        st.json(metrics)
