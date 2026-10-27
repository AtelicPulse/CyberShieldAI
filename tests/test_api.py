"""REST API checks. Skipped automatically if fastapi is not installed."""
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient  # noqa: E402

from core import db  # noqa: E402
from core.api import app  # noqa: E402
from conftest import make_alert  # noqa: E402


@pytest.fixture
def client(tmp_db):
    run = db.start_run("test")
    db.insert_alerts(run, [make_alert(), make_alert(predicted_class="Bot", risk_level="Critical", risk_score=90.0)])
    db.add_counts(run, {"BENIGN": 18, "DoS": 1, "Bot": 1})
    return TestClient(app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_summary_counts(client):
    body = client.get("/summary").json()
    assert body["total"] == 20 and body["attack"] == 2 and "REPLAY SIMULATION" in body["disclaimer"]


def test_alert_filters(client):
    assert len(client.get("/alerts").json()) == 2
    only_bot = client.get("/alerts", params={"attack_class": "Bot"}).json()
    assert [a["predicted_class"] for a in only_bot] == ["Bot"]
    assert len(client.get("/alerts", params={"risk_level": "Low"}).json()) == 0


def test_single_alert_and_not_found(client):
    first = client.get("/alerts").json()[0]["id"]
    assert client.get(f"/alerts/{first}").status_code == 200
    assert client.get("/alerts/999999").status_code == 404


def test_recommend_and_risk_endpoints(client):
    assert client.get("/recommend/DoS/High").json()["immediate"]
    body = client.get("/risk", params={"attack_class": "DDoS", "confidence": 0.9}).json()
    assert 0 < body["risk_score"] <= 100 and body["risk_level"] in ("Low", "Medium", "High", "Critical")


def test_api_is_read_only(client):
    assert client.post("/alerts", json={}).status_code == 405
    assert client.delete("/alerts/1").status_code == 405
