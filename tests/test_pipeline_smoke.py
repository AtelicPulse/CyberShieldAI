"""Day-1 gate: the app must reproduce the predictions the Colab notebook made when it exported the model."""
import json

import numpy as np
import pandas as pd
import pytest

from config import config as cfg
from core.pipeline import predict_flows


def test_first_predictions_match_colab():
    if not (cfg.SMOKE_REFERENCE_PATH.exists() and cfg.HOLDOUT_PATH.exists() and cfg.MODEL_PATH.exists()):
        pytest.skip("export files not found; run colab/export_for_app.py and copy the results here")
    reference = json.loads(cfg.SMOKE_REFERENCE_PATH.read_text())
    holdout = pd.read_parquet(cfg.HOLDOUT_PATH)          # file order, before the replay shuffle
    result = predict_flows(holdout.iloc[reference["rows"]])
    assert result["predicted_class"].tolist() == reference["predicted_class"]
    assert np.allclose(result["confidence"].to_numpy(), reference["confidence"], atol=1e-5)
