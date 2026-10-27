import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd  # noqa: E402
import plotly.graph_objects as go  # noqa: E402
import plotly.express as px  # noqa: E402
import streamlit as st  # noqa: E402

from common import page_setup  # noqa: E402
from config import config as cfg  # noqa: E402
from core import db  # noqa: E402

page_setup("Analytics")

st.markdown("**TELEMETRY BENCHMARK > SESSION REPLAY**")
st.markdown("Simulated traffic distributions and risk classification overview")

# Top-right capture time + export button
hdr_left, hdr_right = st.columns([3, 1])
with hdr_right:
    st.markdown("**Capture Time:** 00:00 - 05:20")
    st.download_button(
        label="Export Stats",
        data="Analytics export placeholder",
        file_name="analytics_export.txt",
        mime="text/plain",
    )

st.divider()

# ---------------------------------------------------------------------------
# Load data (only generate analytics once flows have passed through)
# ---------------------------------------------------------------------------
totals = db.summary()
if totals.get("total", 0) == 0:
    st.info("No telemetry flows have passed through yet. Open Live Monitor and press Start to process flows and generate analytics.")
    st.stop()

alerts = db.alerts_dataframe()

# ---------------------------------------------------------------------------
# Row 1: Flow Classes & Risk Levels
# ---------------------------------------------------------------------------
row1_left, row1_right = st.columns(2)

# --- TOP LEFT: Flows by predicted class (horizontal bar, log scale) --------
with row1_left:
    st.markdown("**[Log Scale]**")
    by_class = pd.Series(totals["by_class"]).rename_axis("class").reset_index(name="flows")
    total_flows = int(by_class["flows"].sum())
    by_class["pct"] = (by_class["flows"] / total_flows * 100).round(1) if total_flows else 0.0

    fig_class = go.Figure()
    fig_class.add_trace(go.Bar(
        x=by_class["flows"],
        y=by_class["class"],
        orientation="h",
        marker_color="#4C8BF5",
        text=[str(p) + "%" for p in by_class["pct"]],
        textposition="outside",
    ))
    fig_class.update_layout(
        title="Flows by predicted class",
        xaxis_type="log",
        xaxis_title="Flow count (log scale)",
        yaxis_title="Class",
        margin=dict(l=10, r=10, t=40, b=10),
        height=350,
    )
    st.plotly_chart(fig_class, use_container_width=True)
    st.caption("Total: {:,}".format(total_flows))

# --- TOP RIGHT: Alerts by risk level (vertical bar) ------------------------
with row1_right:
    LEVEL_COLORS = {
        "Low":      "gray",
        "Medium":   "orange",
        "High":     "darkorange",
        "Critical": "red",
    }
    levels = (
        pd.Series(totals["by_level"])
        .reindex(cfg.RISK_LEVELS)
        .fillna(0)
        .rename_axis("level")
        .reset_index(name="alerts")
    )
    total_attacks = int(levels["alerts"].sum())
    levels["pct"] = (levels["alerts"] / total_attacks * 100).round(1) if total_attacks else 0.0
    bar_colors = [LEVEL_COLORS.get(lv, "#888888") for lv in levels["level"]]

    fig_risk = go.Figure()
    fig_risk.add_trace(go.Bar(
        x=levels["level"],
        y=levels["alerts"],
        marker_color=bar_colors,
        text=[str(int(v)) for v in levels["alerts"]],
        textposition="outside",
    ))
    # Percentage annotations below each bar (inside the plot area)
    pct_annotations = []
    for i, row in levels.iterrows():
        pct_annotations.append(dict(
            x=row["level"],
            y=0,
            text=str(row["pct"]) + "%",
            showarrow=False,
            yanchor="top",
            yshift=-18,
            font=dict(size=11, color="#555555"),
        ))
    fig_risk.update_layout(
        title="Alerts by risk level",
        yaxis_title="Alert count",
        annotations=pct_annotations,
        margin=dict(l=10, r=10, t=40, b=40),
        height=350,
    )
    st.plotly_chart(fig_risk, use_container_width=True)
    st.caption("Weighted threat score  |  Replay alerts flagged: {:,}".format(total_attacks))

# ---------------------------------------------------------------------------
# Row 2: Replay Timeline Analytics
# ---------------------------------------------------------------------------
if not alerts.empty:
    over_time = (
        alerts
        .assign(time=pd.to_datetime(alerts["created_at"]).dt.floor("10s"))
        .groupby("time")
        .size()
        .rename("alerts")
        .reset_index()
    )
    peak_val = int(over_time["alerts"].max())
    avg_val  = over_time["alerts"].mean()
    n_bins   = len(over_time)
    peak_time = over_time.loc[over_time["alerts"].idxmax(), "time"]

    fig_time = px.line(over_time, x="time", y="alerts",
                       title="Alerts per 10 seconds of replay time")
    fig_time.add_annotation(
        x=peak_time,
        y=peak_val,
        text="Peak: " + str(peak_val) + " alerts/10s",
        showarrow=True,
        arrowhead=2,
        ax=40,
        ay=-30,
        font=dict(color="red"),
    )
    fig_time.update_layout(
        xaxis_title="Replay time",
        yaxis_title="Alert count",
        margin=dict(l=10, r=10, t=40, b=10),
        height=350,
    )
    st.plotly_chart(fig_time, use_container_width=True)
    st.caption(
        "Average interval load: {:.0f} alerts/10s  |  "
        "Replay interval window: {} bins".format(avg_val, n_bins)
    )
else:
    st.info("No alert data available for timeline chart.")

# ---------------------------------------------------------------------------
# Simulation context callout
# ---------------------------------------------------------------------------
st.info(
    "Simulation Distribution Context: These distributions reflect the "
    "CIC-IDS2017 research dataset, which intentionally overrepresents "
    "attack traffic for model training purposes. Real enterprise networks "
    "typically see less than 1% malicious flows."
)
