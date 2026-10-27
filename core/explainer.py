"""Per-alert SHAP explanation for the saved tree model."""
import json

import numpy as np

from config import config as cfg
from core.pipeline import feature_names, load_model

_explainer = None


def _get_explainer():
    global _explainer
    if _explainer is None:
        import shap   # imported here so the rest of the app works without it
        _explainer = shap.TreeExplainer(load_model())
    return _explainer


def units():
    # SHAP values are in log-odds for XGBoost and in probability for forests and trees
    return "log-odds" if cfg.MODEL_NAME == "XGBoost" else "probability"


def top_features(flow, predicted_class, k=5):
    """flow: one row (Series or dict) with every feature. Returns the k features that moved the prediction most."""
    names = feature_names()
    x = np.array([[float(flow[name]) for name in names]], dtype=np.float32)
    values = _get_explainer().shap_values(x, check_additivity=False)
    # older SHAP returns a list per class, newer returns (rows, features, classes)
    values = np.stack(values, axis=-1) if isinstance(values, list) else np.asarray(values)
    contribution = values[0, :, cfg.CLASSES.index(predicted_class)]

    stable = set(json.loads(cfg.STABLE_FEATURES_PATH.read_text())) if cfg.STABLE_FEATURES_PATH.exists() else set()
    result = []
    for index in np.argsort(-np.abs(contribution))[:k]:
        result.append({"feature": names[index], "value": float(x[0, index]), "shap": float(contribution[index]),
                       "direction": "raises" if contribution[index] > 0 else "lowers",
                       "stable_across_folds": names[index] in stable})
    return result
