"""Single place for paths, class names and risk-score settings."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# which saved model the app uses; change to "XGBoost" or "DecisionTree" to switch
MODEL_NAME = "XGBoost"
MODEL_DIR = ROOT / "models"
MODEL_PATH = MODEL_DIR / f"{MODEL_NAME}_v0.joblib"
FEATURE_LIST_PATH = MODEL_DIR / "feature_list.json"
STABLE_FEATURES_PATH = MODEL_DIR / "stable_features.json"
SMOKE_REFERENCE_PATH = MODEL_DIR / "smoke_reference.json"
RESULTS_CSV = MODEL_DIR / "model_results.csv"
HOLDOUT_PATH = ROOT / "data" / "sample" / "holdout_flows.parquet"
DB_PATH = ROOT / "data" / "cyber_shield.db"
RECOMMENDATIONS_CSV = ROOT / "config" / "recommendations.csv"

# same order as the research notebooks: the model's class numbers 0..6 follow this list
CLASSES = ["BENIGN", "DoS", "DDoS", "PortScan", "BruteForce", "WebAttack", "Bot"]
ATTACK_CLASSES = CLASSES[1:]
RISK_LEVELS = ["Low", "Medium", "High", "Critical"]

DISCLAIMER = ("REPLAY SIMULATION - NOT LIVE TRAFFIC. Flows are replayed from CIC-IDS2017 data "
              "that was not used to fit the model. Alerts are recommendations only; nothing is blocked.")

# replay settings
REPLAY_ORDER = "shuffled"      # "shuffled" mixes attack types; "chronological" follows the corrected timestamps
REPLAY_SEED = 42
WINDOW_ALERTS = 500            # how many recent alerts count as "recent" for the risk score

# Risk score = 100 * weighted sum of five parts, each between 0 and 1.
# These weights and category values are judgement calls, not fitted to data.
RISK_WEIGHTS = {"category": 0.40, "confidence": 0.25, "volume": 0.15, "breadth": 0.10, "repeat": 0.10}
CATEGORY_WEIGHT = {"DDoS": 0.95, "Bot": 0.90, "DoS": 0.85, "WebAttack": 0.75, "BruteForce": 0.70, "PortScan": 0.40}
VOLUME_CAP = 100               # recent same-class alerts at which the volume part reaches 1
BREADTH_CAP = 20               # distinct destination ports from one source at which breadth reaches 1
REPEAT_CAP = 10                # earlier alerts from one source at which the repeat part reaches 1
LEVEL_THRESHOLDS = (60, 80, 90)   # Low < 60 <= Medium < 80 <= High < 90 <= Critical

# thresholds used by tests/test_safety.py (measured false alarm rates on held-out data were about 0.1% to 0.4%)
TEST_MAX_FALSE_ALARM = 0.02
TEST_MIN_DETECTION = 0.97
