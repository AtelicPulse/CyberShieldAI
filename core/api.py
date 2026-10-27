"""Read-only REST API over the alert database. Start with: uvicorn core.api:app --port 8000"""
from typing import Literal, Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Path, Query
from fastapi.middleware.cors import CORSMiddleware

from config import config as cfg
from core import db
from core.recommend import recommend as lookup_recommendation
from core.risk import risk_level, risk_score

AttackClass = Literal["DoS", "DDoS", "PortScan", "BruteForce", "WebAttack", "Bot"]
Level = Literal["Low", "Medium", "High", "Critical"]

app = FastAPI(title="Cyber Shield AI API", version="1.0.0",
              description="Read-only access to replayed-simulation alerts. " + cfg.DISCLAIMER)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:8501"], allow_methods=["GET"], allow_headers=["*"])


@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/health")
def health():
    return {"status": "ok", "simulation": True}


@app.get("/summary")
def get_summary():
    return {**db.summary(), "disclaimer": cfg.DISCLAIMER}


@app.get("/alerts")
def get_alerts(attack_class: Optional[AttackClass] = None, risk_level_filter: Optional[Level] = Query(None, alias="risk_level"),
               limit: int = Query(100, ge=1, le=1000)):
    filters = {}
    if attack_class:
        filters["class"] = attack_class
    if risk_level_filter:
        filters["level"] = risk_level_filter
    return db.query_alerts(filters, limit)


@app.get("/alerts/{alert_id}")
def get_alert(alert_id: int = Path(..., ge=1)):
    alert = db.get_alert(alert_id)
    if alert is None:
        raise HTTPException(404, f"alert {alert_id} not found")
    return alert


@app.get("/models")
def get_models():
    if not cfg.RESULTS_CSV.exists():
        raise HTTPException(404, "model_results.csv not found")
    return pd.read_csv(cfg.RESULTS_CSV).to_dict(orient="records")


@app.get("/recommend/{attack_class}/{level}")
def get_recommendation(attack_class: AttackClass, level: Level):
    return lookup_recommendation(attack_class, level)


@app.get("/risk")
def get_risk(attack_class: AttackClass, confidence: float = Query(..., ge=0.0, le=1.0),
             recent_events: int = Query(0, ge=0, le=100_000), distinct_targets: int = Query(0, ge=0, le=100_000),
             prior_alerts: int = Query(0, ge=0, le=100_000)):
    score = risk_score(attack_class, confidence, recent_events, distinct_targets, prior_alerts)
    return {"risk_score": score, "risk_level": risk_level(score)}
