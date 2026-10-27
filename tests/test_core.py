"""Risk score, recommendations, database and report. These need no model files."""
import pytest

from config import config as cfg
from core import db
from core.recommend import recommend
from core.report import build_report_html
from core.risk import risk_level, risk_score
from conftest import make_alert


def test_risk_score_stays_between_0_and_100():
    for name in cfg.ATTACK_CLASSES:
        for confidence in (0.0, 0.3, 0.6, 0.99, 1.0):
            for recent in (0, 10, 10_000):
                score = risk_score(name, confidence, recent, 100, 100)
                assert 0 < score <= 100


def test_benign_is_always_zero():
    assert risk_score("BENIGN", 0.99, 500, 50, 50) == 0.0
    assert risk_level(0.0) == "None"


def test_more_confidence_or_activity_never_lowers_the_score():
    for name in cfg.ATTACK_CLASSES:
        assert risk_score(name, 0.99) >= risk_score(name, 0.55)
        assert risk_score(name, 0.8, recent_events=50) >= risk_score(name, 0.8, recent_events=0)
        assert risk_score(name, 0.8, prior_alerts=5) >= risk_score(name, 0.8, prior_alerts=0)


def test_levels_follow_the_thresholds():
    low, medium, high = cfg.LEVEL_THRESHOLDS
    assert risk_level(low - 0.01) == "Low" and risk_level(low) == "Medium"
    assert risk_level(medium) == "High" and risk_level(high) == "Critical" and risk_level(100) == "Critical"


def test_bad_risk_inputs_raise_clean_errors():
    with pytest.raises(ValueError):
        risk_score("NotAClass", 0.5)
    with pytest.raises(ValueError):
        risk_score("DoS", float("nan"))


def test_every_class_and_level_has_a_recommendation():
    for name in cfg.ATTACK_CLASSES:
        for level in cfg.RISK_LEVELS:
            advice = recommend(name, level)
            assert advice["immediate"] and advice["investigation"] and advice["false_positive_note"]
    with pytest.raises(ValueError):
        recommend("DoS", "Extreme")


def test_high_levels_add_containment_steps():
    assert len(recommend("DDoS", "Critical")["immediate"]) > len(recommend("DDoS", "Low")["immediate"])


def test_database_round_trip(tmp_db):
    run = db.start_run("test")
    db.insert_alerts(run, [make_alert(), make_alert(predicted_class="Bot", risk_level="Critical", risk_score=90.0)])
    db.add_counts(run, {"BENIGN": 8, "DoS": 1, "Bot": 1})
    db.add_counts(run, {"BENIGN": 2})   # counts add up across batches
    summary = db.summary(run)
    assert summary["total"] == 12 and summary["attack"] == 2 and summary["by_class"]["BENIGN"] == 10
    assert [a["predicted_class"] for a in db.query_alerts({"class": "Bot"})] == ["Bot"]
    assert len(db.query_alerts(limit=1)) == 1
    alert = db.query_alerts()[0]
    assert db.get_alert(alert["id"])["id"] == alert["id"] and db.get_alert(10 ** 6) is None
    db.save_top_features(alert["id"], [{"feature": "x"}])
    assert "feature" in db.get_alert(alert["id"])["top_features"]


def test_report_has_disclaimer_and_counts(tmp_db):
    db.insert_alerts(db.start_run("test"), [make_alert()])
    html_text = build_report_html(db.alerts_dataframe(), db.summary())
    assert "not live traffic" in html_text and "Alerts by class" in html_text
