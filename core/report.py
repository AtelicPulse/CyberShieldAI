"""HTML report. Table cells are escaped by pandas, and free text is escaped here."""
import html
from datetime import datetime

import pandas as pd

from config import config as cfg


def build_report_html(alerts, summary, model_table=None):
    alerts = pd.DataFrame(alerts) if not isinstance(alerts, pd.DataFrame) else alerts
    parts = [
        "<html><head><meta charset='utf-8'><title>Cyber Shield AI report</title></head><body>",
        "<h1>Cyber Shield AI report</h1>",
        f"<p><b>Note: this report is based on replayed CIC-IDS2017 flows, not live traffic.</b></p>",
        f"<p>{html.escape(cfg.DISCLAIMER)}</p>",
        f"<p>Generated {datetime.now().isoformat(timespec='seconds')}. Model: {html.escape(cfg.MODEL_NAME)}.</p>",
        f"<p>Flows processed: {int(summary['total'])}. Flagged as attacks: {int(summary['attack'])}.</p>",
        "<h2>Alerts by class</h2>",
        pd.Series(summary["by_class"], name="flows").rename_axis("class").reset_index().to_html(index=False),
        "<h2>Alerts by risk level</h2>",
        pd.Series(summary["by_level"], name="alerts").rename_axis("risk level").reset_index().to_html(index=False),
    ]
    if not alerts.empty:
        parts += ["<h2>Alerts per minute</h2>",
                  alerts.assign(minute=alerts["created_at"].str[:16]).groupby("minute").size()
                  .rename("alerts").reset_index().to_html(index=False)]
        sources = alerts.dropna(subset=["src_ip"]).groupby("src_ip").size().sort_values(ascending=False).head(10)
        parts += ["<h2>Top 10 source addresses</h2>", sources.rename("alerts").reset_index().to_html(index=False)]
        shown = ["id", "created_at", "predicted_class", "confidence", "risk_score", "risk_level", "src_ip", "dst_port"]
        parts += ["<h2>Most recent alerts (up to 200)</h2>", alerts[shown].head(200).round(3).to_html(index=False)]
    if model_table is not None and not model_table.empty:
        parts += ["<h2>Model results from the research experiments</h2>", model_table.round(4).to_html(index=False)]
    parts.append("</body></html>")
    return "\n".join(parts)


def csv_safe(frame):
    """CSV text where cells starting with = + - @ get a leading quote, so spreadsheets do not run them as formulas."""
    frame = frame.copy()
    for column in frame.select_dtypes(include="object"):
        frame[column] = frame[column].map(lambda v: "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v)
    return frame.to_csv(index=False)
