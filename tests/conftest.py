"""Shared fixtures. Set CSA_SYNTHETIC=1 to run the whole suite against a small made-up model
(this tests the code, not the research model). Without it, model tests use the real files or are skipped."""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import config as cfg  # noqa: E402

SYNTHETIC = os.environ.get("CSA_SYNTHETIC") == "1"


def _build_synthetic(folder):
    import joblib
    from sklearn.ensemble import RandomForestClassifier
    names = [f"feature_{i}" for i in range(8)]
    rng = np.random.default_rng(0)
    labels = rng.choice(len(cfg.CLASSES), size=6000, p=[0.7, 0.06, 0.06, 0.06, 0.04, 0.04, 0.04])
    values = rng.normal(size=(6000, 8)) + 3.0 * labels[:, None]   # classes are far apart, so the model learns them
    model = RandomForestClassifier(n_estimators=30, random_state=0).fit(values, labels)
    cfg.MODEL_PATH = folder / "model.joblib"
    cfg.FEATURE_LIST_PATH = folder / "feature_list.json"
    joblib.dump(model, cfg.MODEL_PATH)
    cfg.FEATURE_LIST_PATH.write_text(json.dumps(names))
    test_labels = rng.choice(len(cfg.CLASSES), size=3000, p=[0.7, 0.06, 0.06, 0.06, 0.04, 0.04, 0.04])
    holdout = pd.DataFrame(rng.normal(size=(3000, 8)) + 3.0 * test_labels[:, None], columns=names)
    holdout["true_label"] = [cfg.CLASSES[i] for i in test_labels]
    return holdout


@pytest.fixture(scope="session")
def model_env(tmp_path_factory):
    """Returns a holdout DataFrame (features + true_label) and makes config point at a usable model."""
    from core import pipeline
    if SYNTHETIC:
        holdout = _build_synthetic(tmp_path_factory.mktemp("synthetic"))
    elif cfg.MODEL_PATH.exists() and cfg.FEATURE_LIST_PATH.exists() and cfg.HOLDOUT_PATH.exists():
        holdout = pd.read_parquet(cfg.HOLDOUT_PATH)
    else:
        pytest.skip("model files not found (copy models/ and data/sample/, or set CSA_SYNTHETIC=1)")
    pipeline.reset_cache()
    return holdout


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    from core import db
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "test.db")
    db.init_db()
    return cfg.DB_PATH


def make_alert(**overrides):
    alert = {"flow_row": 1, "true_label": "DoS", "predicted_class": "DoS", "confidence": 0.9, "risk_score": 60.0,
             "risk_level": "High", "src_ip": "10.0.0.5", "dst_ip": "10.0.0.9", "dst_port": 80, "flow_ts": "2017-07-05"}
    alert.update(overrides)
    return alert
