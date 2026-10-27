"""Deterministic lookup from (attack class, risk level) to defensive steps. The app never acts on them."""
import pandas as pd

from config import config as cfg

_table = None


def _load():
    global _table
    if _table is None:
        _table = pd.read_csv(cfg.RECOMMENDATIONS_CSV).set_index(["attack_class", "risk_level"])
    return _table


def recommend(attack_class, level):
    if attack_class == "BENIGN" or level == "None":
        return {"immediate": [], "investigation": [], "false_positive_note": ""}
    try:
        row = _load().loc[(attack_class, level)]
    except KeyError:
        raise ValueError(f"no recommendation for {attack_class!r} at level {level!r}") from None
    return {
        "immediate": row["immediate"].split("|"),
        "investigation": row["investigation"].split("|"),
        "false_positive_note": row["false_positive_note"],
    }
