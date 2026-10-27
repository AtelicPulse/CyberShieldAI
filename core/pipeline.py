"""Loads the saved model once and turns flow features into a predicted class and a confidence."""
import json

import joblib
import numpy as np
import pandas as pd

from config import config as cfg

_model = None
_features = None


def reset_cache():
    global _model, _features
    _model, _features = None, None


def feature_names():
    global _features
    if _features is None:
        _features = json.loads(cfg.FEATURE_LIST_PATH.read_text())
    return _features


def load_model():
    global _model
    if _model is None:
        _model = joblib.load(cfg.MODEL_PATH)   # raises FileNotFoundError if the file is missing
        if list(_model.classes_) != list(range(len(cfg.CLASSES))):
            raise ValueError("model classes do not match config.CLASSES")
    return _model


def predict_flows(flows):
    """flows: DataFrame holding every feature column. Returns predicted_class and confidence, same index."""
    missing = [name for name in feature_names() if name not in flows.columns]
    if missing:
        raise ValueError(f"missing feature columns, for example {missing[:3]}")
    values = flows[feature_names()].to_numpy(dtype=np.float32)
    if not np.isfinite(values).all():
        # the training data had no inf or NaN rows, so a clean error is safer than a silent guess
        raise ValueError("flow features contain NaN or infinite values")
    probabilities = load_model().predict_proba(values)
    best = probabilities.argmax(axis=1)
    return pd.DataFrame({"predicted_class": [cfg.CLASSES[i] for i in best],
                         "confidence": probabilities[np.arange(len(best)), best]}, index=flows.index)
