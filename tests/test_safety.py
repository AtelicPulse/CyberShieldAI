"""Safety checks: odd inputs, error handling, false alarms and misses on held-out data, and the disclaimer.
Model tests use the real model files, or a synthetic model when CSA_SYNTHETIC=1."""
import numpy as np
import pandas as pd
import pytest

from config import config as cfg
from core import db, pipeline
from core.pipeline import feature_names, predict_flows


def _row(model_env, value):
    return pd.DataFrame([{name: value for name in feature_names()}])


def test_extreme_but_finite_inputs_give_a_valid_class(model_env):
    for value in (0.0, 1e9, -1.0):
        result = predict_flows(_row(model_env, value))
        assert result["predicted_class"].iloc[0] in cfg.CLASSES
        assert 0.0 <= result["confidence"].iloc[0] <= 1.0


def test_nan_and_infinite_inputs_are_rejected_cleanly(model_env):
    for bad in (np.nan, np.inf, -np.inf):
        row = _row(model_env, 0.0)
        row.iloc[0, 0] = bad
        with pytest.raises(ValueError):
            predict_flows(row)


def test_missing_columns_are_rejected_cleanly(model_env):
    with pytest.raises(ValueError):
        predict_flows(_row(model_env, 0.0).drop(columns=[feature_names()[0]]))


def test_false_alarm_rate_on_benign_flows_is_low(model_env):
    benign = model_env[model_env["true_label"] == "BENIGN"]
    sample = benign.sample(min(5000, len(benign)), random_state=42)
    rate = (predict_flows(sample)["predicted_class"] != "BENIGN").mean()
    print(f"\n  benign flows tested: {len(sample)}, false alarm rate: {rate:.4f}")
    assert rate <= cfg.TEST_MAX_FALSE_ALARM


def test_detection_rate_on_attack_flows_is_high(model_env):
    attacks = model_env[model_env["true_label"] != "BENIGN"]
    sample = attacks.sample(min(5000, len(attacks)), random_state=42)
    rate = (predict_flows(sample)["predicted_class"] != "BENIGN").mean()
    print(f"\n  attack flows tested: {len(sample)}, detection rate: {rate:.4f}")
    assert rate >= cfg.TEST_MIN_DETECTION


def test_every_attack_class_is_detected_at_least_sometimes(model_env):
    # an overall rate can hide a class the model never catches, so check each class on its own
    for name in cfg.ATTACK_CLASSES:
        rows = model_env[model_env["true_label"] == name]
        if len(rows) < 20:
            continue
        caught = (predict_flows(rows.head(500))["predicted_class"] != "BENIGN").mean()
        assert caught >= 0.5, f"{name}: only {caught:.2f} of flows flagged as an attack"


def test_missing_model_file_raises_a_clear_error(monkeypatch):
    monkeypatch.setattr(cfg, "MODEL_PATH", cfg.ROOT / "models" / "does_not_exist.joblib")
    pipeline.reset_cache()
    with pytest.raises(FileNotFoundError):
        pipeline.load_model()
    pipeline.reset_cache()   # do not leave a half-loaded state for other tests


def test_database_is_created_when_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(cfg, "DB_PATH", tmp_path / "new_folder" / "fresh.db")
    db.init_db()
    assert cfg.DB_PATH.exists() and db.summary()["total"] == 0


def test_every_app_page_shows_the_simulation_disclaimer():
    assert "NOT LIVE TRAFFIC" in cfg.DISCLAIMER and "nothing is blocked" in cfg.DISCLAIMER
    common = (cfg.ROOT / "app" / "common.py").read_text()
    assert "st.warning(cfg.DISCLAIMER)" in common            # the banner itself
    pages = [cfg.ROOT / "app" / "main.py", *sorted((cfg.ROOT / "app" / "pages").glob("*.py"))]
    assert len(pages) == 5
    for page in pages:
        assert "page_setup(" in page.read_text(), f"{page.name} does not call page_setup, so it shows no disclaimer"
