import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import streamlit as st

from common import page_setup
from config import config as cfg
from core import db
from core.report import build_report_html, csv_safe


page_setup("History and Reports")
st.caption("AUDIT TRAIL > SIMULATION RUN ARCHIVE")
st.caption(
    "Full telemetry archive with model predictions, ground truth alignment, "
    "and downloadable audit reports."
)


if "history_preset" not in st.session_state:
    st.session_state["history_preset"] = "none"


alerts_full = db.alerts_dataframe({}, 20_000)

totals = {"total": 0, "attack": 0}
if not alerts_full.empty:
    totals["total"] = len(alerts_full)
    if "predicted_class" in alerts_full.columns:
        totals["attack"] = int(
            (alerts_full["predicted_class"].str.lower() != "benign").sum()
        )

# Ground truth agreement
gt_agreement = 0.0
if (
    not alerts_full.empty
    and "true_label" in alerts_full.columns
    and "predicted_class" in alerts_full.columns
):
    matched = (alerts_full["true_label"] == alerts_full["predicted_class"]).sum()
    gt_agreement = round(100.0 * matched / max(len(alerts_full), 1), 1)

attack_pct = (
    round(100.0 * totals["attack"] / max(totals["total"], 1), 1)
    if totals["total"] > 0
    else 0.0
)


model_table = pd.read_csv(cfg.RESULTS_CSV) if cfg.RESULTS_CSV.exists() else None


hdr_left, hdr_right = st.columns([3, 2])
with hdr_right:
    btn_cols = st.columns(2)
    # Prepare download data (use full dataset for the report; filtered for CSV
    # is generated after filtering below, so we use a placeholder here and
    # re-render after filtering)
    _csv_placeholder = btn_cols[0].empty()
    _html_placeholder = btn_cols[1].empty()


with st.container(border=True):
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Archived Flows", f"{totals['total']:,}")
    m2.metric(
        "Flagged Incidents",
        f"{totals['attack']:,}",
        delta=f"{attack_pct}% of total",
    )
    with m3:
        st.metric("Exported Reports", "1")
        st.caption("Latest: this session")


fc1, fc2, fc3, fc4 = st.columns([2, 2, 3, 1])
with fc1:
    chosen_class = st.selectbox(
        "Attack Class", ["All Classes"] + list(cfg.ATTACK_CLASSES)
    )
with fc2:
    chosen_level = st.selectbox(
        "Risk Level", ["All Risk Levels"] + list(cfg.RISK_LEVELS)
    )
with fc3:
    search_text = st.text_input("Search Flow / IP / Port", value="")
with fc4:
    limit = st.number_input(
        "Rows", min_value=10, max_value=20_000, value=1_000, step=100
    )

st.markdown("**Quick Presets**")
p1, p2, p3, p4 = st.columns(4)

no_filter_active = (
    chosen_class == "All Classes"
    and chosen_level == "All Risk Levels"
    and search_text.strip() == ""
)

with p1:
    replay_label = "> Run Active Replay" if no_filter_active else "Run Active Replay"
    if st.button(replay_label, use_container_width=True):
        st.session_state["history_preset"] = "none"
        st.rerun()
with p2:
    if st.button("Mismatched Predictions Only", use_container_width=True):
        st.session_state["history_preset"] = "mismatch"
        st.rerun()
with p3:
    if st.button("Critical Severity Only", use_container_width=True):
        st.session_state["history_preset"] = "critical"
        st.rerun()
with p4:
    if st.button("External Inbound Scans (Port 80/443)", use_container_width=True):
        st.session_state["history_preset"] = "external"
        st.rerun()

preset = st.session_state["history_preset"]


filters = {}
if chosen_class != "All Classes":
    filters["class"] = chosen_class
if chosen_level != "All Risk Levels":
    filters["level"] = chosen_level

alerts = db.alerts_dataframe(filters, int(limit))


if not alerts.empty:
    if preset == "mismatch":
        if "true_label" in alerts.columns and "predicted_class" in alerts.columns:
            alerts = alerts[alerts["true_label"] != alerts["predicted_class"]]
    elif preset == "critical":
        if "risk_level" in alerts.columns:
            alerts = alerts[alerts["risk_level"] == "Critical"]
    elif preset == "external":
        if "dst_port" in alerts.columns:
            alerts = alerts[alerts["dst_port"].isin([80, 443])]

# Apply free-text search
if not alerts.empty and search_text.strip():
    mask = pd.Series(False, index=alerts.index)
    for col in alerts.select_dtypes(include="object").columns:
        mask |= alerts[col].astype(str).str.contains(
            search_text.strip(), case=False, na=False
        )
    alerts = alerts[mask]


st.subheader("Historical Network Flows & Predictions")
st.caption("Replay Batch | GET /api/alerts | Showing filtered results")
st.caption("Risk Indicators: Critical (Red) | High (Orange) | Medium (Yellow) | Low (Green) | Alignment (MATCH / MISMATCH)")

if alerts.empty:
    st.info("No alerts match the current filters or preset.")
else:
    # Build display dataframe with required columns
    display_cols_map = {
        "id": "id",
        "run_id": "RUN",
        "created_at": "TIMESTAMP",
        "true_label": "TRUE LABEL",
        "predicted_class": "PREDICTED CLASS",
        "confidence": "confidence",
        "risk_score": "risk_score",
        "risk_level": "risk_level",
        "src_ip": "SOURCE",
    }

    available = [c for c in display_cols_map if c in alerts.columns]
    shown = alerts[available].copy()

    # Compute agreement column
    if "true_label" in shown.columns and "predicted_class" in shown.columns:
        shown.insert(
            shown.columns.tolist().index("predicted_class") + 1,
            "agreement",
            shown.apply(
                lambda r: "MATCH" if r["true_label"] == r["predicted_class"] else "MISMATCH",
                axis=1,
            ),
        )

    # Rename columns for display
    rename_map = {k: v for k, v in display_cols_map.items() if k in shown.columns}
    shown = shown.rename(columns=rename_map)

    # Elegant dark-theme highlighting for risk levels and classification agreement
    def _style_risk_level(val):
        v = str(val).capitalize()
        if v == "Critical":
            return "color: #f87171; font-weight: 700; background-color: rgba(239, 68, 68, 0.15);"
        if v == "High":
            return "color: #fb923c; font-weight: 700; background-color: rgba(249, 115, 22, 0.15);"
        if v == "Medium":
            return "color: #facc15; font-weight: 600; background-color: rgba(234, 179, 8, 0.12);"
        if v == "Low":
            return "color: #4ade80; font-weight: 600; background-color: rgba(34, 197, 94, 0.12);"
        return ""

    def _style_agreement(val):
        if str(val) == "MATCH":
            return "color: #34d399; font-weight: 700; background-color: rgba(16, 185, 129, 0.12);"
        if str(val) == "MISMATCH":
            return "color: #f87171; font-weight: 700; background-color: rgba(239, 68, 68, 0.15);"
        return ""

    styled = shown.style
    if "risk_level" in shown.columns:
        styled = styled.map(_style_risk_level, subset=["risk_level"])
    if "agreement" in shown.columns:
        styled = styled.map(_style_agreement, subset=["agreement"])

    col_config = {
        "risk_score": st.column_config.ProgressColumn(
            "RISK SCORE",
            format="%.1f",
            min_value=0,
            max_value=100,
        ),
        "confidence": st.column_config.NumberColumn(
            "CONFIDENCE",
            format="%.4f",
        ),
        "agreement": st.column_config.TextColumn(
            "AGREEMENT",
        ),
        "risk_level": st.column_config.TextColumn(
            "RISK LEVEL",
        ),
    }

    st.dataframe(styled, column_config=col_config, hide_index=True, use_container_width=True)
    st.caption(
        f"Showing 1-{min(int(limit), len(shown))} of {len(alerts_full):,} flows"
    )

    # Populate top download buttons now that we have filtered data
    _csv_placeholder.download_button(
        label="Export CSV / JSON",
        data=csv_safe(shown),
        file_name="alerts.csv",
        mime="text/csv",
        use_container_width=True,
    )
    _html_placeholder.download_button(
        label="Generate Audit Report",
        data=build_report_html(alerts, db.summary(), model_table),
        file_name="cyber_shield_report.html",
        mime="text/html",
        type="primary",
        use_container_width=True,
    )


st.info(
    "Student Analyst Guide -- Why audit historical telemetry? "
    "Historical flow archives let you correlate model predictions with ground truth labels, "
    "identify systematic false positives, and build datasets for model improvement. "
    "In a real SOC, this data feeds into threat hunting and retrospective analysis workflows."
)
