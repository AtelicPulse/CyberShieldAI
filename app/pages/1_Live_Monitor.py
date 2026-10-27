import sys
from pathlib import Path

import pandas as pd
import streamlit as st  # type: ignore[import-not-found]

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # lets this page import app/common.py
from common import get_session, page_setup, reset_session  # noqa: E402
from core import db  # noqa: E402
from core.simulation import process_batch  # noqa: E402
from config import config as cfg  # noqa: E402

page_setup("Live Monitor")
ss = get_session()

SHOWN = ["id", "created_at", "predicted_class", "confidence", "risk_score", "risk_level", "src_ip", "dst_port"]


ctrl_left, ctrl_right = st.columns([3, 2])

with ctrl_left:
    btn_col1, btn_col2, btn_col3 = st.columns(3)

    if btn_col1.button(
        "Start",
        use_container_width=True,
        type="primary" if not ss.running else "secondary",
    ):
        ss.running = True
        st.rerun()

    if btn_col2.button(
        "Pause",
        use_container_width=True,
        type="primary" if ss.running else "secondary",
    ):
        ss.running = False
        st.rerun()

    if btn_col3.button("Reset", use_container_width=True):
        reset_session()
        st.rerun()

with ctrl_right:
    ss.speed = st.slider("Flows per second", 10, 200, int(getattr(ss, "speed", 50)), step=10)


if ss.running:
    st.success(f"RUNNING: streaming {ss.speed} flows/sec")
else:
    st.info("PAUSED: Click Start to begin streaming")



# Fragment: all live-updating content

def highlight(row):
    colour = {"Critical": "#f5b5b5", "High": "#fbd9a5"}.get(row["risk_level"], "")
    return [f"background-color: {colour}; color: #000" if colour else ""] * len(row)


@st.fragment(run_every=1.0)
def monitor():
    speed = int(getattr(ss, "speed", 50))
    last_batch_info = None

    if ss.running and not ss.stream.finished:
        batch = ss.stream.next_batch(speed)
        alerts, counts = process_batch(batch, ss.state)
        db.insert_alerts(ss.run_id, alerts)
        db.add_counts(ss.run_id, counts)
        ss.recent = db.query_alerts({"run_id": ss.run_id}, limit=50)   # read back so ids match the database
        benign_in_batch = counts.get("BENIGN", 0)
        attack_in_batch = len(alerts)
        last_batch_info = (len(batch), benign_in_batch, attack_in_batch)

    totals = db.summary(ss.run_id)
    total_flows = totals["total"]
    total_attacks = totals["attack"]
    total_benign = total_flows - total_attacks
    urgent = totals["by_level"].get("High", 0) + totals["by_level"].get("Critical", 0)
    total_holdout = max(1, len(ss.stream.holdout))
    pos = ss.stream.position
    progress_frac = min(1.0, pos / total_holdout)
    pct = progress_frac * 100


    # Replay Progress

    remaining_flows = max(0, total_holdout - pos)
    if speed > 0:
        remaining_secs = remaining_flows / speed
    else:
        remaining_secs = 0
    rem_m = int(remaining_secs // 60)
    rem_s = int(remaining_secs % 60)

    st.markdown(f"**Replay progress:** {pos:,} / {total_holdout:,} flows ({pct:.1f}%)")
    st.progress(progress_frac)
    st.caption(f"Estimated remaining: {rem_m}m {rem_s}s")


    # 4 Metric Cards

    with st.container(border=True):
        m1, m2, m3, m4 = st.columns(4)

        with m1:
            st.markdown("**Flows processed**")
            st.markdown(f"<span style='font-size:1.5rem'>{total_flows:,}</span>", unsafe_allow_html=True)

        with m2:
            st.markdown("**Predicted normal**")
            st.markdown(
                f"<span style='font-size:1.5rem; color:#2e7d32'>{total_benign:,}</span>",
                unsafe_allow_html=True,
            )

        with m3:
            st.markdown("**Flagged attacks**")
            st.markdown(
                f"<span style='font-size:1.5rem; color:#c62828'>{total_attacks:,}</span>",
                unsafe_allow_html=True,
            )

        with m4:
            st.markdown("**High or Critical**")
            st.markdown(
                f"<span style='font-size:1.5rem; color:#c62828'>{urgent:,}</span>",
                unsafe_allow_html=True,
            )

        if last_batch_info:
            n_batch, n_benign, n_atk = last_batch_info
            st.caption(f"Last second: {n_batch} flows in -- {n_benign} normal, {n_atk} flagged")
        else:
            st.caption("Last second: no batch processed")


    # Latest Alerts

    st.subheader("Latest Alerts")
    st.caption("Real-time candidate intrusion flows detected during dataset playback")

    filter_left, filter_right = st.columns(2)
    with filter_left:
        toggle_empty = st.button("Toggle Empty State Test", type="secondary", key="toggle_empty_btn")
        if toggle_empty:
            ss._empty_test = not getattr(ss, "_empty_test", False)

    with filter_right:
        sev_filter = st.selectbox(
            "Severity filter",
            ["All Severities", "Critical", "High", "Medium", "Low"],
            label_visibility="collapsed",
            key="sev_filter",
        )

    empty_test = getattr(ss, "_empty_test", False)
    recent = [] if empty_test else (ss.recent or [])

    if recent:
        df = pd.DataFrame(recent)[SHOWN]
        if sev_filter != "All Severities":
            df = df[df["risk_level"] == sev_filter]

        if df.empty:
            st.info(f"No alerts match severity filter: {sev_filter}")
        else:
            styled = df.style.apply(highlight, axis=1).format(
                {"confidence": "{:.2f}", "risk_score": "{:.1f}"}
            )
            st.dataframe(
                styled,
                height=400,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "risk_level": st.column_config.TextColumn("Risk Level"),
                    "confidence": st.column_config.NumberColumn("Confidence", format="%.2f"),
                    "risk_score": st.column_config.NumberColumn("Risk Score", format="%.1f"),
                },
            )
    elif total_flows > 0 and not empty_test:
        st.info("All flows processed so far have been BENIGN (normal traffic). No attack alerts have been triggered yet.")
    else:
        st.info("No alerts to display.")

    if ss.stream.finished:
        st.warning(
            "The replay has reached the end of the held-out flows dataset. "
            "Click Reset to start from the beginning."
        )



    st.info(
        "**Analyst Training Mode** -- "
        "This dashboard replays captured network flows through the detection model. "
        "Use it to practice triage, understand model decisions, and build intuition for real SOC workflows."
    )

    # Footer

    model_name = getattr(cfg, "MODEL_NAME", "unknown")
    st.caption(
        f"Model: {model_name}. "
        "Tested only on held-out flows from the same capture days as training. "
        "Confidence Threshold: 0.85. Zero Defensive Interventions."
    )


monitor()
