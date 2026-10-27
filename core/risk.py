"""Risk score from 0 to 100 and the Low / Medium / High / Critical level."""
import math

from config import config as cfg


def risk_score(attack_class, confidence, recent_events=0, distinct_targets=0, prior_alerts=0):
    """Weighted sum of five parts, each scaled to 0..1. BENIGN is always 0."""
    if attack_class == "BENIGN":
        return 0.0
    if attack_class not in cfg.CATEGORY_WEIGHT:
        raise ValueError(f"unknown attack class: {attack_class!r}")
    if not math.isfinite(confidence):
        raise ValueError("confidence must be a finite number")

    confidence = min(max(float(confidence), 0.0), 1.0)
    # logs, so the first few events matter more than the hundredth
    volume = min(1.0, math.log1p(max(recent_events, 0)) / math.log1p(cfg.VOLUME_CAP))
    breadth = min(1.0, max(distinct_targets, 0) / cfg.BREADTH_CAP)
    repeat = min(1.0, max(prior_alerts, 0) / cfg.REPEAT_CAP)

    weights = cfg.RISK_WEIGHTS
    total = (weights["category"] * cfg.CATEGORY_WEIGHT[attack_class]
             + weights["confidence"] * confidence
             + weights["volume"] * volume
             + weights["breadth"] * breadth
             + weights["repeat"] * repeat)
    return round(100 * total, 2)


def risk_level(score):
    if score <= 0:
        return "None"
    low, medium, high = cfg.LEVEL_THRESHOLDS
    if score < low:
        return "Low"
    if score < medium:
        return "Medium"
    if score < high:
        return "High"
    return "Critical"
