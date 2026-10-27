"""Measures speed, memory and size of the prediction pipeline and writes docs/performance_report.md.
Run from the project root:  python tests/performance.py
Every number in the report is measured here or read from models/model_results.csv; nothing is typed in by hand."""
import os
import sys
import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd
import psutil

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import config as cfg  # noqa: E402
from core.pipeline import feature_names, load_model, predict_flows  # noqa: E402

ASSUMED_WATTS = 15   # an assumption for a laptop CPU under load, not a measurement


def to_md(frame):
    header = "| " + " | ".join(map(str, frame.columns)) + " |"
    divider = "|" + "---|" * len(frame.columns)
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in frame.itertuples(index=False)]
    return "\n".join([header, divider, *rows])


holdout = pd.read_parquet(cfg.HOLDOUT_PATH).sample(5000, random_state=42)
flows = holdout[feature_names()]
load_model()
predict_flows(flows.head(10))   # warm-up

latency = []
for n in (1, 10, 100, 1000):
    times = []
    for _ in range(5):
        start = time.perf_counter()
        predict_flows(flows.head(n))
        times.append(time.perf_counter() - start)
    latency.append({"batch_rows": n, "median_ms": round(1000 * float(np.median(times)), 2),
                    "us_per_flow": round(1e6 * float(np.median(times)) / n, 1)})

start_wall, start_cpu = time.perf_counter(), time.process_time()
for _ in range(10):
    predict_flows(flows.head(1000))
wall, cpu = time.perf_counter() - start_wall, time.process_time() - start_cpu
throughput = 10_000 / wall

tracemalloc.start()
predict_flows(flows.head(2000))
peak_mb = tracemalloc.get_traced_memory()[1] / 1e6
tracemalloc.stop()
rss_mb = psutil.Process(os.getpid()).memory_info().rss / 1e6

sizes = {path.name: round(path.stat().st_size / 1e6, 1) for path in (cfg.MODEL_PATH, cfg.HOLDOUT_PATH, cfg.DB_PATH) if path.exists()}
joules_per_1000_flows = ASSUMED_WATTS * cpu / 10

report = [f"# Performance report ({cfg.MODEL_NAME})", "", "Measured by `tests/performance.py` on this machine.", "",
          f"Machine: {psutil.cpu_count(logical=False)} physical cores, {psutil.virtual_memory().total / 1e9:.1f} GB RAM.", "",
          "## Prediction latency", "", to_md(pd.DataFrame(latency)), "",
          f"## Throughput", "", f"About {throughput:,.0f} flows per second in batches of 1000. The dashboard replays at 10 to 200 flows per second.", "",
          "## Memory", "", f"Process memory (RSS): {rss_mb:.0f} MB. Peak extra allocation for a 2000-flow batch: {peak_mb:.1f} MB.", "",
          "## File sizes (MB)", "", ", ".join(f"{k}: {v}" for k, v in sizes.items()), "",
          "## Energy (rough)", "", f"CPU time per 1000 flows: {1000 * cpu / 10_000:.3f} s. With an assumed {ASSUMED_WATTS} W CPU this is "
          f"about {joules_per_1000_flows:.2f} J per 1000 flows. The wattage is an assumption, so treat this as an order of magnitude.", ""]

if cfg.RESULTS_CSV.exists():
    results = pd.read_csv(cfg.RESULTS_CSV)
    report += ["## Research results (copied from models/model_results.csv)", "",
               to_md(results.round(4)), "",
               f"The app uses {cfg.MODEL_NAME}, trained on the baseline setup (no SMOTE, no feature selection)."]

Path(cfg.ROOT / "docs").mkdir(exist_ok=True)
(cfg.ROOT / "docs" / "performance_report.md").write_text("\n".join(report))
print("written docs/performance_report.md")
