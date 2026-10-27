"""Replays held-out flows through the model and turns attack predictions into scored alerts."""
from collections import Counter, deque

import numpy as np
import pandas as pd

from config import config as cfg
from core.pipeline import predict_flows
from core.risk import risk_level, risk_score


def load_holdout():
    holdout = pd.read_parquet(cfg.HOLDOUT_PATH)
    if cfg.REPLAY_ORDER == "chronological" and "ts" in holdout and holdout["ts"].notna().any():
        holdout = holdout.sort_values("ts", kind="stable")
    else:
        holdout = holdout.sample(frac=1.0, random_state=cfg.REPLAY_SEED)
    # the row number in this order is the alert's flow_row, so the detail page can find the flow again
    return holdout.reset_index(drop=True)


class ReplayStream:
    def __init__(self, holdout=None):
        self.holdout = load_holdout() if holdout is None else holdout
        self.position = 0

    @property
    def finished(self):
        return self.position >= len(self.holdout)

    def next_batch(self, n):
        batch = self.holdout.iloc[self.position:self.position + n]
        self.position += len(batch)
        return batch

    def reset(self):
        self.position = 0


def new_state():
    return {"window": deque(maxlen=cfg.WINDOW_ALERTS), "source_counts": Counter()}


def _text(value):
    return None if pd.isna(value) else str(value)


def process_batch(batch, state):
    """Returns (alerts, class_counts). Risk uses only alerts seen so far in this run."""
    if batch.empty:
        return [], {}
    predictions = predict_flows(batch)
    class_counts = predictions["predicted_class"].value_counts().to_dict()
    window, source_counts = state["window"], state["source_counts"]

    alerts = []
    for row_number, predicted, confidence in zip(batch.index, predictions["predicted_class"], predictions["confidence"]):
        if predicted == "BENIGN":
            continue
        row = batch.loc[row_number]
        src_ip = _text(row.get("src_ip", np.nan))
        dst_port = None if pd.isna(row.get("dst_port", np.nan)) else int(row["dst_port"])
        recent_same_class = sum(1 for item in window if item[0] == predicted)
        targets = {item[2] for item in window if src_ip and item[1] == src_ip and item[2] is not None}
        score = risk_score(predicted, float(confidence), recent_same_class, len(targets),
                           source_counts[src_ip] if src_ip else 0)
        alerts.append({"flow_row": int(row_number), "true_label": _text(row.get("true_label", np.nan)),
                       "predicted_class": predicted, "confidence": float(confidence), "risk_score": score,
                       "risk_level": risk_level(score), "src_ip": src_ip, "dst_ip": _text(row.get("dst_ip", np.nan)),
                       "dst_port": dst_port, "flow_ts": _text(row.get("ts", np.nan))})
        window.append((predicted, src_ip, dst_port))
        if src_ip:
            source_counts[src_ip] += 1
    return alerts, class_counts
