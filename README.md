# Cyber Shield AI (prototype)

Replays held-out CIC-IDS2017 flows through a trained model, gives each detected attack a risk level,
explains it with SHAP, and suggests defensive steps. **It is a replay simulation, not live monitoring, and it never blocks traffic.**

## Set up
1. In Colab, run `colab/export_for_app.py`. It writes `ids_paper/app_export.zip`.
2. Unzip it into this folder so that `models/` and `data/sample/` are filled.
3. `pip install -r requirements.txt` (keep scikit-learn and xgboost at the pinned versions, because the model file depends on them).
4. `pytest tests/ -v` (with the real files) or `CSA_SYNTHETIC=1 pytest tests/ -v` (checks the code against a made-up model).

## Run
- `./run.sh` opens the dashboard at http://localhost:8501. Press Start on the Live Monitor page.
- `./run_api.sh` (second terminal) serves the read-only REST API at http://localhost:8000/docs, bound to localhost only.
- `python tests/performance.py` writes `docs/performance_report.md` from measured numbers.

## Layout
`config/` paths, class names, risk weights, recommendations table. `core/` pipeline, risk, recommend, explainer, simulation, db, report, api.
`app/` Streamlit pages. `tests/` pytest suite. `colab/` export script.

## Honest limits
- The model was trained without SMOTE or feature selection, on the 70 flow features. It has not been tested on later or different traffic yet.
- The replay uses flows the final model never fitted: held-out benign flows, plus the research tuning rows (these helped choose settings but not fit the model).
- The risk score is a hand-weighted heuristic and model confidence is not calibrated. Weights are in `config/config.py`.
- SHAP explanations are approximate, and different models rank features differently.
