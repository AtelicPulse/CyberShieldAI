"""Security checks: SQL injection, input validation, HTML and CSV escaping, paths."""
import pandas as pd
import pytest

from config import config as cfg
from core import db
from core.report import build_report_html, csv_safe
from conftest import SYNTHETIC, make_alert

PAYLOADS = ["' OR '1'='1", "'; DROP TABLE alerts; --", "1 UNION SELECT * FROM runs --", "admin'--"]


def test_sql_injection_through_db_filters_returns_nothing_and_changes_nothing(tmp_db):
    db.insert_alerts(db.start_run("test"), [make_alert()])
    for payload in PAYLOADS:
        for key in ("class", "level", "src_ip"):
            assert db.query_alerts({key: payload}) == []
    assert len(db.query_alerts()) == 1   # table still exists and the row is still there


def test_db_rejects_unknown_filter_columns(tmp_db):
    with pytest.raises(ValueError):
        db.query_alerts({"predicted_class = 'x' OR 1": "y"})


def test_get_alert_is_not_injectable(tmp_db):
    db.insert_alerts(db.start_run("test"), [make_alert()])
    with pytest.raises((ValueError, TypeError)):
        db.get_alert("1 OR 1=1")


def test_api_rejects_bad_input(tmp_db):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from core.api import app
    client = TestClient(app)
    for payload in PAYLOADS:
        assert client.get("/alerts", params={"attack_class": payload}).status_code == 422
    assert client.get("/alerts", params={"risk_level": "EXTREME"}).status_code == 422
    assert client.get("/alerts", params={"limit": 99999}).status_code == 422
    assert client.get("/alerts", params={"limit": -1}).status_code == 422
    assert client.get("/alerts/-1").status_code == 422
    assert client.get("/risk", params={"attack_class": "DoS", "confidence": 1.5}).status_code == 422
    assert client.get("/recommend/FakeAttack/High").status_code == 422
    assert client.get("/recommend/DoS/EXTREME").status_code == 422


def test_html_report_escapes_attacker_controlled_text(tmp_db):
    evil = pd.DataFrame([{"id": 1, "created_at": "2025-01-01T00:00:00", "predicted_class": "<script>alert(1)</script>",
                          "confidence": 0.9, "risk_score": 50.0, "risk_level": "High", "src_ip": "<img src=x onerror=alert(1)>",
                          "dst_port": 80}])
    html_text = build_report_html(evil, {"total": 1, "attack": 1, "by_class": {"<script>": 1}, "by_level": {"High": 1}})
    assert "<script>" not in html_text and "<img src=x" not in html_text
    assert "&lt;script&gt;" in html_text


def test_csv_export_neutralises_spreadsheet_formulas():
    frame = pd.DataFrame({"src_ip": ["=HYPERLINK(\"http://bad\")", "+1", "-1", "@SUM(A1)", "10.0.0.1"]})
    lines = csv_safe(frame).splitlines()[1:]
    assert all(line.lstrip('"').startswith("'") for line in lines[:4]) and lines[4] == "10.0.0.1"


def test_configured_paths_stay_inside_the_project():
    paths = [cfg.HOLDOUT_PATH, cfg.DB_PATH, cfg.RECOMMENDATIONS_CSV, cfg.RESULTS_CSV]
    if not SYNTHETIC:   # the synthetic mode deliberately points the model at a temporary folder
        paths.append(cfg.MODEL_PATH)
    for path in paths:
        assert cfg.ROOT in path.resolve().parents or path.resolve() == cfg.ROOT, f"{path} is outside the project"
