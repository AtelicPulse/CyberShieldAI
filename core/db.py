"""SQLite storage. Every query that includes user-supplied values uses ? placeholders."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import pandas as pd

from config import config as cfg

# the only columns a caller may filter on: keys are the names callers use, values are column names
FILTER_COLUMNS = {"class": "predicted_class", "level": "risk_level", "run_id": "run_id", "src_ip": "src_ip"}
ALERT_COLUMNS = ["run_id", "created_at", "flow_row", "true_label", "predicted_class", "confidence",
                 "risk_score", "risk_level", "src_ip", "dst_ip", "dst_port", "flow_ts"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT, started_at TEXT NOT NULL, model TEXT NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, created_at TEXT NOT NULL,
    flow_row INTEGER, true_label TEXT, predicted_class TEXT NOT NULL, confidence REAL,
    risk_score REAL, risk_level TEXT, src_ip TEXT, dst_ip TEXT, dst_port INTEGER, flow_ts TEXT,
    top_features TEXT);
CREATE TABLE IF NOT EXISTS counts (
    run_id INTEGER NOT NULL, predicted_class TEXT NOT NULL, n INTEGER NOT NULL,
    PRIMARY KEY (run_id, predicted_class));
CREATE INDEX IF NOT EXISTS idx_alerts_class ON alerts (predicted_class);
CREATE INDEX IF NOT EXISTS idx_alerts_level ON alerts (risk_level);
"""


@contextmanager
def connect():
    cfg.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(cfg.DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")   # lets the dashboard and the API read while the replay writes
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def init_db():
    with connect() as connection:
        connection.executescript(SCHEMA)


def start_run(model_name, note=""):
    with connect() as connection:
        cursor = connection.execute("INSERT INTO runs (started_at, model, note) VALUES (?, ?, ?)",
                                    (datetime.now().isoformat(timespec="seconds"), model_name, note))
        return cursor.lastrowid


def insert_alerts(run_id, alerts):
    if not alerts:
        return
    now = datetime.now().isoformat(timespec="seconds")
    rows = [(run_id, now, a.get("flow_row"), a.get("true_label"), a["predicted_class"], a.get("confidence"),
             a.get("risk_score"), a.get("risk_level"), a.get("src_ip"), a.get("dst_ip"), a.get("dst_port"),
             a.get("flow_ts")) for a in alerts]
    with connect() as connection:
        connection.executemany(
            f"INSERT INTO alerts ({', '.join(ALERT_COLUMNS)}) VALUES ({', '.join('?' * len(ALERT_COLUMNS))})", rows)


def add_counts(run_id, class_counts):
    with connect() as connection:
        connection.executemany(
            "INSERT INTO counts (run_id, predicted_class, n) VALUES (?, ?, ?) "
            "ON CONFLICT(run_id, predicted_class) DO UPDATE SET n = n + excluded.n",
            [(run_id, name, int(n)) for name, n in class_counts.items()])


def query_alerts(filters=None, limit=100):
    clauses, values = [], []
    for key, value in (filters or {}).items():
        if key not in FILTER_COLUMNS:
            raise ValueError(f"cannot filter on {key!r}")
        clauses.append(f"{FILTER_COLUMNS[key]} = ?")
        values.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit = max(1, min(int(limit), 100_000))
    with connect() as connection:
        rows = connection.execute(f"SELECT * FROM alerts {where} ORDER BY id DESC LIMIT ?", (*values, limit)).fetchall()
    return [dict(row) for row in rows]


def alerts_dataframe(filters=None, limit=20_000):
    return pd.DataFrame(query_alerts(filters, limit))


def get_alert(alert_id):
    with connect() as connection:
        row = connection.execute("SELECT * FROM alerts WHERE id = ?", (int(alert_id),)).fetchone()
    return dict(row) if row else None


def save_top_features(alert_id, features):
    with connect() as connection:
        connection.execute("UPDATE alerts SET top_features = ? WHERE id = ?", (json.dumps(features), int(alert_id)))


def summary(run_id=None):
    where, values = ("WHERE run_id = ?", (run_id,)) if run_id is not None else ("", ())
    with connect() as connection:
        class_rows = connection.execute(
            f"SELECT predicted_class, SUM(n) AS n FROM counts {where} GROUP BY predicted_class", values).fetchall()
        level_rows = connection.execute(
            f"SELECT risk_level, COUNT(*) AS n FROM alerts {where} GROUP BY risk_level", values).fetchall()
    by_class = {row["predicted_class"]: row["n"] for row in class_rows}
    total = sum(by_class.values())
    return {"total": total, "attack": total - by_class.get("BENIGN", 0), "by_class": by_class,
            "by_level": {row["risk_level"]: row["n"] for row in level_rows}}
