import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json

import pandas as pd
import plotly.express as px
import streamlit as st

from common import page_setup, replay_holdout
from core import db, explainer
from core.recommend import recommend

page_setup("Alert Detail")

recent = db.query_alerts(limit=200)
if not recent:
    st.info("No alerts yet. Open Live Monitor and press Start.")
    st.stop()


if "alert_idx" not in st.session_state:
    st.session_state.alert_idx = 0

st.session_state.alert_idx = max(0, min(st.session_state.alert_idx, len(recent) - 1))


def _fmt(a):
    ts = str(a.get("timestamp", ""))[:8] if a.get("timestamp") else "??:??:??"
    return f"#{a['id']} -- {a['predicted_class']} -- {ts} -- {a['risk_level']} Risk"

top_col1, top_col2, top_col3, top_col4 = st.columns([4, 2, 1, 1])

with top_col1:
    labels = {i: _fmt(a) for i, a in enumerate(recent)}
    chosen_idx = st.selectbox(
        "SELECT ALERT",
        options=list(labels.keys()),
        index=st.session_state.alert_idx,
        format_func=labels.get,
    )
    st.session_state.alert_idx = chosen_idx

with top_col2:
    st.markdown(
        "<div style='padding-top:28px; font-size:0.85rem; color:#888;'>Buffer: 200 Replay Flows Cached</div>",
        unsafe_allow_html=True,
    )

with top_col3:
    st.markdown("<div style='padding-top:22px;'></div>", unsafe_allow_html=True)
    if st.button("Prev Flow", use_container_width=True, type="secondary"):
        st.session_state.alert_idx = max(0, st.session_state.alert_idx - 1)
        st.rerun()

with top_col4:
    st.markdown("<div style='padding-top:22px;'></div>", unsafe_allow_html=True)
    if st.button("Next Flow", use_container_width=True, type="secondary"):
        st.session_state.alert_idx = min(len(recent) - 1, st.session_state.alert_idx + 1)
        st.rerun()

alert = db.get_alert(recent[st.session_state.alert_idx]["id"])

# ---------------------------------------------------------------------------
# INCIDENT HEADER
# ---------------------------------------------------------------------------
_risk_colors = {
    "CRITICAL": "#c0392b",
    "HIGH":     "#e67e22",
    "MEDIUM":   "#f1c40f",
    "LOW":      "#95a5a6",
}
risk_level_upper = str(alert.get("risk_level", "")).upper()
risk_color = _risk_colors.get(risk_level_upper, "#95a5a6")

incident_ts = str(alert.get("timestamp", "N/A"))

st.markdown(
    f"<p style='font-variant:small-caps; letter-spacing:0.12em; color:#aaa; margin-bottom:2px;'>"
    f"INCIDENT CLASSIFICATION #{alert['id']}</p>",
    unsafe_allow_html=True,
)

badge_col, ts_col = st.columns([1, 4])
with badge_col:
    st.markdown(
        f"<span style='background:{risk_color}; color:#fff; padding:3px 10px; "
        f"border-radius:4px; font-weight:bold; font-size:0.85rem;'>{risk_level_upper}</span>",
        unsafe_allow_html=True,
    )
with ts_col:
    st.markdown(
        f"<span style='color:#aaa; font-size:0.85rem;'>{incident_ts}</span>",
        unsafe_allow_html=True,
    )


predicted_class = alert.get("predicted_class", "Unknown")

_subtitle_map = {
    "DoS":         "Volumetric SYN flood anomaly pattern",
    "DDoS":        "Distributed denial-of-service flood pattern",
    "PortScan":    "Network reconnaissance scan pattern",
    "BruteForce":  "Credential stuffing / brute force login pattern",
    "WebAttack":   "Web application exploit attempt pattern",
    "Bot":         "Automated bot / C2 beacon pattern",
}
subtitle = _subtitle_map.get(predicted_class, "Anomalous network flow pattern")

_class_display_map = {
    "DoS":        "Denial of Service (DoS)",
    "DDoS":       "Distributed Denial of Service (DDoS)",
    "PortScan":   "Port Scan",
    "BruteForce": "Brute Force",
    "WebAttack":  "Web Attack",
    "Bot":        "Bot / C2 Beacon",
    "BENIGN":     "Benign Traffic",
}
attack_display = _class_display_map.get(predicted_class, predicted_class)

st.markdown(f"# {attack_display}")
st.markdown(f"*{subtitle}*")


confidence = alert.get("confidence", 0.0)
dst_ip     = alert.get("dst_ip", "N/A")
dst_port   = alert.get("dst_port", "N/A")
src_ip     = alert.get("src_ip", "N/A")
src_port   = alert.get("src_port", alert.get("src_port", "N/A")) if "src_port" in alert else "N/A"

m1, m2, m3 = st.columns(3)
m1.metric("Model Confidence", f"{confidence:.2f}")
m2.metric("Target", f"{dst_ip}:{dst_port}")
m3.metric("Source", f"{src_ip}:{src_port}")

st.markdown("---")


left_col, right_col = st.columns([3, 2])


with left_col:
    st.subheader("Why was this flagged?")
    st.markdown(
        "<span style='background:#1a3a5c; color:#7ec8e3; padding:2px 8px; "
        "border-radius:3px; font-size:0.78rem; font-weight:bold;'>Local SHAP Values</span>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#aaa; font-size:0.85rem; margin-top:6px;'>"
        "Feature contributions that pushed this flow toward the predicted class.</p>",
        unsafe_allow_html=True,
    )

    features = json.loads(alert["top_features"]) if alert.get("top_features") else None
    if features is None:
        try:
            with st.spinner("Computing the SHAP explanation..."):
                flow = replay_holdout().iloc[alert["flow_row"]]
                features = explainer.top_features(flow, alert["predicted_class"])
                db.save_top_features(alert["id"], features)
        except ImportError:
            st.error("The shap package is not installed. Run: pip install shap")

    if features:
        table = pd.DataFrame(features)
        figure = px.bar(
            table.iloc[::-1],
            x="shap",
            y="feature",
            color="direction",
            orientation="h",
            color_discrete_map={"raises": "#c0392b", "lowers": "#2874a6"},
            title=f"Feature Contributions -- SHAP Values ({explainer.units()})",
        )
        st.plotly_chart(figure, use_container_width=True)
        st.dataframe(
            table.rename(columns={"stable_across_folds": "stable across CV folds"}),
            hide_index=True,
        )

    st.markdown("#### Raw Flow Snapshot")
    with st.container(border=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        fc1.metric("Protocol",        "TCP(6)")
        fc2.metric("Flags",           "SYN Flags")
        fc3.metric("Est. Flows/sec",  "N/A")
        fc4.metric("TTL Variance",    "N/A")


with right_col:
    st.subheader("GROUND TRUTH ALIGNMENT")
    true_label = alert.get("true_label", "N/A")

    with st.container(border=True):
        st.markdown("**Dataset:** CIC-IDS2017-Eval")
        if str(true_label).strip().lower() == str(predicted_class).strip().lower():
            st.success(
                f"Dataset label: {true_label} -- model agrees. "
                "Both annotation and model score identify anomalous traffic."
            )
        else:
            st.error(
                f"Dataset label: {true_label} -- MISMATCH. "
                f"Model predicted {predicted_class}."
            )
        st.info(
            "Alternative scenario: BENIGN -- false alarm | Eval Ref"
        )
